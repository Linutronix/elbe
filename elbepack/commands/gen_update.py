# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2014-2017 Linutronix GmbH

import argparse
import logging
import os
import sys

from elbepack.elbeproject import ElbeProject
from elbepack.elbexml import ValidationError
from elbepack.log import elbe_logging
from elbepack.updatepkg import MissingData, gen_update_pkg


def run_command(argv):

    aparser = argparse.ArgumentParser(prog='elbe gen_update')
    aparser.add_argument('-t', '--target', dest='target',
                         help='directoryname of target')
    aparser.add_argument('-o', '--output', dest='output',
                         help='filename of the update package')
    aparser.add_argument('-n', '--name', dest='name',
                         help='name of the project (included in the report)')
    aparser.add_argument(
        '-p',
        '--pre-sh',
        dest='presh_file',
        help='script that is executed before the update will be applied')
    aparser.add_argument(
        '-P',
        '--post-sh',
        dest='postsh_file',
        help='script that is executed after the update was applied')
    aparser.add_argument('-c', '--cfg-dir', dest='cfg_dir',
                         help='files that are copied to target')
    aparser.add_argument('-x', '--cmd-dir', dest='cmd_dir',
                         help='scripts that are executed on the target')
    aparser.add_argument('--skip-validation', action='store_true',
                         dest='skip_validation', default=False,
                         help='Skip xml schema validation')
    aparser.add_argument('--buildtype', dest='buildtype',
                         help='Override the buildtype')
    aparser.add_argument('--debug', action='store_true', dest='debug',
                         default=False,
                         help='Enable various features to debug the build')
    aparser.add_argument('xmlfile', nargs='?')

    args = aparser.parse_args(argv)

    if args.xmlfile is None and (not args.cfg_dir and not args.cmd_dir):
        aparser.error('xmlfile is not specificied and neither --cfg-dir nor --cmd-dir are given')

    if args.xmlfile is not None and not args.target:
        aparser.error('No target specified')

    if not args.output:
        aparser.error('No output file specified')

    with elbe_logging({'streams': sys.stdout}):
        try:
            project = ElbeProject(args.target, name=args.name,
                                  override_buildtype=args.buildtype,
                                  skip_validate=args.skip_validation)
        except ValidationError:
            logging.exception('XML validation failed.  Bailing out')
            sys.exit(34)

    if args.presh_file:
        if not os.path.isfile(args.presh_file):
            logging.error('pre.sh file does not exist')
            sys.exit(35)
        project.presh_file = args.presh_file

    if args.postsh_file:
        if not os.path.isfile(args.postsh_file):
            logging.error('post.sh file does not exist')
            sys.exit(36)
        project.postsh_file = args.postsh_file

    update_xml = None
    if len(args) >= 1:
        update_xml = args[0]

    with elbe_logging({'projects': project.builddir}):
        try:
            gen_update_pkg(project, update_xml, args.output, args.uildtype,
                           args.skip_validation, args.debug,
                           cfg_dir=args.cfg_dir, cmd_dir=args.cmd_dir)

        except ValidationError:
            logging.exception('XML validation failed.  Bailing out')
            sys.exit(37)
        except MissingData:
            logging.exception('Missing Data')
            sys.exit(38)
