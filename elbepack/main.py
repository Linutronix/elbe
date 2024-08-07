# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2013-2017 Linutronix GmbH

import argparse
import importlib
import pkgutil
import sys

import elbepack.commands
from elbepack.cli import format_exception
from elbepack.version import elbe_version


def get_cmdlist():
    return [x for _, x, _ in pkgutil.iter_modules(elbepack.commands.__path__)]


def main(argv=sys.argv):
    parser = argparse.ArgumentParser(prog='elbe')
    parser.add_argument('--version', action='version', version=f'%(prog)s v{elbe_version}')
    parser.add_argument('--stacktrace-on-error', action='store_true', dest='stacktrace_on_error')
    parser.add_argument('--propagate-exception', action='store_true', dest='propagate_exception',
                        help=argparse.SUPPRESS)

    subparsers = parser.add_subparsers(required=True, dest='cmd')

    for cmd in get_cmdlist():
        subparsers.add_parser(cmd)

    args, cmd_argv = parser.parse_known_args(argv[1:])

    cmdmod = importlib.import_module('.' + args.cmd, elbepack.commands.__name__)

    try:
        cmdmod.run_command(cmd_argv)
    except Exception as e:
        if args.propagate_exception:
            raise e
        sys.exit(format_exception(e, output=sys.stderr,
                                  base_module=elbepack,
                                  verbose=args.stacktrace_on_error))
