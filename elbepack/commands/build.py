# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Linutronix GmbH

import argparse

from elbepack.buildsubmitaction import XmlOrIso, add_submit_arguments, build_dir_type
from elbepack.cli import add_argument, add_arguments_from_decorated_function
from elbepack.commands.preprocess import add_xmlpreprocess_passthrough_arguments
from elbepack.localbuildaction import local_build_with_repodir_and_dl_result


@add_submit_arguments
@add_argument(
    '--build-dir', dest='build_dir', type=build_dir_type, default='',
    help='directory where to save output files and the internal build cache '
         '(default is a timestamped directory in the current working directory)')
@add_argument('input', type=XmlOrIso, metavar='<xmlfile> | <isoimage>')
def _build(args):
    with args.input as resolved:
        local_build_with_repodir_and_dl_result(
            resolved.xmlfile, resolved.cdrom, args.base_image, args)


def run_command(argv):
    aparser = argparse.ArgumentParser(prog='elbe build')

    add_xmlpreprocess_passthrough_arguments(aparser)
    add_arguments_from_decorated_function(aparser, _build)

    args = aparser.parse_args(argv)
    args.parser = aparser

    _build(args)
