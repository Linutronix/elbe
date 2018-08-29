# ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (c) 2014, 2017 Manuel Traut <manut@linutronix.de>
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import print_function

from elbepack.dbaction import DbAction


def run_command(argv):

    if not argv:
        print("elbe db - no action given")
        DbAction.print_actions()
        return

    try:
        DbAction(argv[0]).execute(argv[1:])
    except KeyError:
        print("elbe db - unknown action given")
        DbAction.print_actions()
        return

    return
