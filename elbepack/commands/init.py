# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2014-2015, 2017, 2018 Linutronix GmbH

import argparse

from elbepack.commands import add_deprecated_argparse_argument
from elbepack.config import cfg
from elbepack.init import create_initvm
from elbepack.log import elbe_logging


def run_command(argv):

    aparser = argparse.ArgumentParser(prog='elbe init')

    aparser.add_argument('--skip-validation', action='store_true',
                         dest='skip_validation', default=False,
                         help='Skip xml schema validation')

    aparser.add_argument('--directory', dest='directory', default='./build',
                         help='Working directory (default is build)',
                         metavar='FILE')

    aparser.add_argument(
        '--cdrom',
        dest='cdrom',
        help='Use FILE as cdrom iso, and use that to build the initvm',
        metavar='FILE')

    aparser.add_argument('--buildtype', dest='buildtype',
                         help='Override the buildtype')

    aparser.add_argument(
        '--debug',
        dest='debug',
        action='store_true',
        default=False,
        help='start qemu in graphical mode to enable console switch')

    add_deprecated_argparse_argument(aparser, '--nesting', nargs=0)
    add_deprecated_argparse_argument(aparser, '--devel', nargs=0)

    aparser.add_argument(
        '--skip-build-bin',
        action='store_false',
        dest='build_bin',
        default=True,
        help='Skip building Binary Repository CDROM, for exact Reproduction')

    aparser.add_argument(
        '--skip-build-sources',
        action='store_false',
        dest='build_sources',
        default=True,
        help='Skip building Source CDROM')

    aparser.add_argument('--fail-on-warning', action='store_true',
                         dest='fail_on_warning', default=False,
                         help=argparse.SUPPRESS)

    aparser.add_argument('xmlfile')

    args = aparser.parse_args(argv)

    with elbe_logging({'files': None}):
        create_initvm(
            cfg['initvm_domain'],
            args.xmlfile,
            args.directory,
            skip_validation=args.skip_validation,
            buildtype=args.buildtype,
            cdrom=args.cdrom,
            build_bin=args.build_bin,
            build_sources=args.build_sources,
            fail_on_warning=args.fail_on_warning,
        )
