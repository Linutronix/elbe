# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2015-2017 Linutronix GmbH

import os
import sys
from optparse import OptionParser

from elbepack.initvmaction import InitVMAction, InitVMError
from elbepack.xmlpreprocess import PreprocessWrapper


def run_command(argv):
    oparser = OptionParser(usage='usage: elbe initvm [options] <command>')

    oparser.add_option(
        '--directory',
        dest='directory',
        default=None,
        help='directory, where the initvm resides, default is ./initvm')

    oparser.add_option('--cdrom', dest='cdrom', default=None,
                       help='iso image of Binary cdrom')

    oparser.add_option(
        '--devel',
        action='store_true',
        dest='devel',
        default=False,
        help='Install elbe Version from the current working into initvm')

    oparser.add_option('--skip-download', action='store_true',
                       dest='skip_download', default=False,
                       help='Skip downloading generated Files')

    oparser.add_option('--output', dest='outdir', default=None,
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

    oparser.add_option(
        '--nesting',
        dest='nesting',
        action='store_true',
        default=False,
        help='allow initvm to support nested kvm. '
             'This makes /proc/cpuinfo inside initvm differ per host.')

    oparser.add_option(
        '--build-sdk',
        dest='build_sdk',
        action='store_true',
        default=False,
        help="Also make 'initvm submit' build an SDK.")

    oparser.add_option('--qemu', action='store_true',
                       dest='qemu_mode', default=False,
                       help='Use QEMU direct instead of libvirtd.')

    PreprocessWrapper.add_options(oparser)

    (opt, args) = oparser.parse_args(argv)

    if not args:
        print('elbe initvm - no subcommand given', file=sys.stderr)
        InitVMAction.print_actions()
        sys.exit(48)

    directory = opt.directory or os.getcwd() + '/initvm'

    # Use absolute Path
    directory = os.path.abspath(directory)

    try:
        action = InitVMAction(args[0], qemu_mode=opt.qemu_mode)
    except KeyError:
        print('elbe initvm - unknown subcommand', file=sys.stderr)
        InitVMAction.print_actions()
        sys.exit(49)

    try:
        action.execute(directory, opt, args[1:])
    except InitVMError as e:
        print('InitVM Exception', file=sys.stderr)
        print(e, file=sys.stderr)
        sys.exit(50)
