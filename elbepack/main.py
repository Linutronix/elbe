# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2013-2017 Linutronix GmbH

import argparse
import importlib
import pkgutil
import sys

import elbepack.commands
from elbepack.version import elbe_version


def get_cmdlist():
    return [x for _, x, _ in pkgutil.iter_modules(elbepack.commands.__path__)]


def main(argv=sys.argv):
    parser = argparse.ArgumentParser(prog='elbe')
    parser.add_argument('--version', action='version', version=f'%(prog)s v{elbe_version}')

    subparsers = parser.add_subparsers(required=True, dest='cmd')

    for cmd in get_cmdlist():
        subparsers.add_parser(cmd)

    args, cmd_argv = parser.parse_known_args(argv[1:])

    modname = 'elbepack.commands.' + args.cmd

    cmdmod = importlib.import_module(modname)

    cmdmod.run_command(cmd_argv)
