# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2014, 2017 Linutronix GmbH

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
