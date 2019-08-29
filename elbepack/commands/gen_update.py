# ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (c) 2014-2015 Torben Hohn <torbenh@linutronix.de>
# Copyright (c) 2014-2015, 2017 Manuel Traut <manut@linutronix.de>
# Copyright (c) 2014 Stefan Gast <stefan.gast@linutronix.de>
# Copyright (c) 2017 Kurt Kanzenbach <kurt@linutronix.de>
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import print_function

from optparse import OptionParser
import sys
import os
import logging

from elbepack.elbeproject import ElbeProject
from elbepack.elbexml import ValidationError
from elbepack.updatepkg import gen_update_pkg, MissingData
from elbepack.log import elbe_logging


def run_command(argv):

    # pylint: disable=too-many-statements
    # pylint: disable=too-many-branches

    oparser = OptionParser(usage="usage: %prog gen_update [options] [xmlfile]")
    oparser.add_option("-t", "--target", dest="target",
                       help="directoryname of target")
    oparser.add_option("-o", "--output", dest="output",
                       help="filename of the update package")
    oparser.add_option("-n", "--name", dest="name",
                       help="name of the project (included in the report)")
    oparser.add_option(
        "-p",
        "--pre-sh",
        dest="presh_file",
        help="script that is executed before the update will be applied")
    oparser.add_option(
        "-P",
        "--post-sh",
        dest="postsh_file",
        help="script that is executed after the update was applied")
    oparser.add_option("-c", "--cfg-dir", dest="cfg_dir",
                       help="files that are copied to target")
    oparser.add_option("-x", "--cmd-dir", dest="cmd_dir",
                       help="scripts that are executed on the target")
    oparser.add_option("--skip-validation", action="store_true",
                       dest="skip_validation", default=False,
                       help="Skip xml schema validation")
    oparser.add_option("--buildtype", dest="buildtype",
                       help="Override the buildtype")
    oparser.add_option("--debug", action="store_true", dest="debug",
                       default=False,
                       help="Enable various features to debug the build")

    (opt, args) = oparser.parse_args(argv)

    if len(args) != 1:
        if not opt.cfg_dir and not opt.cmd_dir:
            oparser.print_help()
            sys.exit(20)

    if len(args) == 1 and not opt.target:
        print("No target specified")
        sys.exit(20)

    if not opt.output:
        print("No output file specified")
        sys.exit(20)

    if opt.buildtype:
        buildtype = opt.buildtype
    else:
        buildtype = None

    with elbe_logging({"streams":sys.stdout}):
        try:
            project = ElbeProject(opt.target, name=opt.name,
                                  override_buildtype=buildtype,
                                  skip_validate=opt.skip_validation)
        except ValidationError:
            logging.exception("XML validation failed.  Bailing out")
            sys.exit(20)

    if opt.presh_file:
        if not os.path.isfile(opt.presh_file):
            logging.error('pre.sh file does not exist')
            sys.exit(20)
        project.presh_file = opt.presh_file

    if opt.postsh_file:
        if not os.path.isfile(opt.postsh_file):
            logging.error('post.sh file does not exist')
            sys.exit(20)
        project.postsh_file = opt.postsh_file

    update_xml = None
    if len(args) >= 1:
        update_xml = args[0]

    with elbe_logging({"projects":project.builddir}):
        try:
            gen_update_pkg(project, update_xml, opt.output, buildtype,
                           opt.skip_validation, opt.debug,
                           cfg_dir=opt.cfg_dir, cmd_dir=opt.cmd_dir)

        except ValidationError:
            logging.exception("XML validation failed.  Bailing out")
            sys.exit(20)
        except MissingData:
            logging.exception("Missing Data")
            sys.exit(20)
