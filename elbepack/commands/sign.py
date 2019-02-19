# ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (c) 2014 Stefan Gast <stefan.gast@linutronix.de>
# Copyright (c) 2014-2015, 2017 Manuel Traut <manut@linutronix.de>
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import print_function

from elbepack.egpg import sign_file


def run_command(argv):
    if len(argv) != 2:
        print("Wrong number of arguments.")
        print("Please pass the name of the file to sign "
              "and a valid gnupg fingerprint.")
        return
    else:
        sign_file(argv[0], argv[1])
