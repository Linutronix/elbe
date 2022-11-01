# ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (c) 2014 Stefan Gast <stefan.gast@linutronix.de>
# Copyright (c) 2014, 2017 Manuel Traut <manut@linutronix.de>
#
# SPDX-License-Identifier: GPL-3.0-or-later

from elbepack.egpg import unsign_file


def run_command(argv):
    if len(argv) != 1:
        print("Wrong number of arguments.")
        print("Please pass the name of the file to unsign.")
        return

    fname = unsign_file(argv[0])
    if fname:
        print(f"unsigned file: {fname}")
    else:
        print("removing signature failed")
