# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2013-2017 Linutronix GmbH

import importlib
import pkgutil
import sys

import elbepack.commands
from elbepack.version import elbe_version


def get_cmdlist():
    return [x for _, x, _ in pkgutil.iter_modules(elbepack.commands.__path__)]


def usage():
    print('elbe v%s' % elbe_version)
    print("need a subcommand: e.g. \'elbe initvm\'. \n\
    Available subcommands are: \n")
    for i in get_cmdlist():
        print('        * %s' % i)


def main(argv=sys.argv):
    if len(argv) < 2:
        usage()
        sys.exit(20)

    if argv[1] == '--version':
        print('elbe v%s' % (elbe_version))
        sys.exit(0)

    cmd_list = get_cmdlist()

    if argv[1] not in cmd_list:
        print('Unknown subcommand !\n')
        usage()
        sys.exit(20)

    modname = 'elbepack.commands.' + argv[1]

    cmdmod = importlib.import_module(modname)

    cmdmod.run_command(argv[2:])
