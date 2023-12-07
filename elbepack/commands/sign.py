# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2014-2015, 2017 Linutronix GmbH

from elbepack.egpg import sign_file


def run_command(argv):
    if len(argv) != 2:
        print('Wrong number of arguments.')
        print('Please pass the name of the file to sign '
              'and a valid gnupg fingerprint.')
        return
    sign_file(argv[0], argv[1])
