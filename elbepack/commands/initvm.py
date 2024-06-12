# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2015-2017 Linutronix GmbH

import datetime
import os
import sys
from optparse import OptionParser, SUPPRESS_HELP

from elbepack.commands import add_deprecated_optparse_option
from elbepack.commands.preprocess import add_xmlpreprocess_passthrough_options
from elbepack.initvmaction import InitVMAction


def run_command(argv):
    oparser = OptionParser(usage='usage: elbe initvm [options] <command>')

    oparser.add_option(
        '--directory',
        dest='directory',
        default=None,
        help='directory, where the initvm resides, default is ./initvm')

    oparser.add_option('--cdrom', dest='cdrom', default=None,
                       help='iso image of Binary cdrom')

    oparser.add_option('--skip-download', action='store_true',
                       dest='skip_download', default=False,
                       help='Skip downloading generated Files')

    oparser.add_option('--output', dest='outdir',
                       default='elbe-build-' + datetime.datetime.now().strftime('%Y%m%d-%H%M%S'),
                       help='directory where to save downloaded Files')

    oparser.add_option(
        '--skip-build-bin',
        action='store_false',
        dest='build_bin',
        default=True,
        help='Skip building Binary Repository CDROM, for exact Reproduction')

    oparser.add_option('--skip-build-sources', action='store_false',
                       dest='build_sources', default=True,
                       help='Skip building Source CDROM')

    oparser.add_option('--keep-files', action='store_true',
                       dest='keep_files', default=False,
                       help="don't delete elbe project files in initvm")

    oparser.add_option('--writeproject', dest='writeproject', default=None,
                       help='write project name to file')

    add_deprecated_optparse_option(oparser, '--nesting')
    add_deprecated_optparse_option(oparser, '--devel')

    oparser.add_option(
        '--build-sdk',
        dest='build_sdk',
        action='store_true',
        default=False,
        help="Also make 'initvm submit' build an SDK.")

    oparser.add_option('--qemu', action='store_true',
                       dest='qemu_mode', default=False,
                       help='Use QEMU direct instead of libvirtd.')

    oparser.add_option('--fail-on-warning', action='store_true',
                       dest='fail_on_warning', default=False,
                       help=SUPPRESS_HELP)

    add_xmlpreprocess_passthrough_options(oparser)

    (opt, args) = oparser.parse_args(argv)

    if not args:
        print('elbe initvm - no subcommand given', file=sys.stderr)
        InitVMAction.print_actions()
        sys.exit(48)

    directory = opt.directory or os.getcwd() + '/initvm'

    # Use absolute Path
    directory = os.path.abspath(directory)

    try:
        action_class = InitVMAction.get_action_class(args[0])
    except KeyError:
        print('elbe initvm - unknown subcommand', file=sys.stderr)
        InitVMAction.print_actions()
        sys.exit(49)

    action = action_class(directory=directory, opt=opt)
    action.execute(opt, args[1:])
