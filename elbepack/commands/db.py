# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2014, 2017 Linutronix GmbH

from elbepack.dbaction import DbAction


def run_command(argv):

    if not argv:
        print('elbe db - no action given')
        DbAction.print_actions()
        return

    try:
        DbAction(argv[0]).execute(argv[1:])
    except KeyError:
        print('elbe db - unknown action given')
        DbAction.print_actions()
        return

    return
