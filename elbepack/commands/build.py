# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Linutronix GmbH

import argparse
import datetime
import os

from elbepack.buildsubmitaction import add_submit_arguments, extract_cdrom
from elbepack.cli import add_argument, add_arguments_from_decorated_function
from elbepack.commands.preprocess import add_xmlpreprocess_passthrough_arguments
from elbepack.localbuildaction import local_build_with_repodir_and_dl_result


@add_submit_arguments
@add_argument(
    '--build-dir', dest='build_dir', type=os.path.abspath,
    help='directory where to save output files and the internal build cache '
         '(default is a timestamped directory in the current working directory)')
@add_argument('input', metavar='<xmlfile> | <isoimage>')
def _build(args):
    if args.build_dir is None:
        args.build_dir = os.path.abspath(
            'elbe-build-' + datetime.datetime.now().strftime('%Y%m%d-%H%M%S'))

    cdrom = None
    xmlfile = args.input
    if xmlfile.endswith('.iso'):
        tmp = extract_cdrom(xmlfile)
        cdrom = xmlfile
        xmlfile = tmp.fname('source.xml')
    elif not xmlfile.endswith('.xml'):
        args.parser.error('Unknown file ending (use either xml or iso)')

    local_build_with_repodir_and_dl_result(xmlfile, cdrom, args.base_image, args)


def run_command(argv):
    aparser = argparse.ArgumentParser(prog='elbe build')

    add_xmlpreprocess_passthrough_arguments(aparser)
    add_arguments_from_decorated_function(aparser, _build)

    args = aparser.parse_args(argv)
    args.parser = aparser

    _build(args)
