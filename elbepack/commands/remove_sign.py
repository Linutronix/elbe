# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2014, 2017 Linutronix GmbH

import argparse

from elbepack.egpg import unsign_file


def run_command(argv):
    parser = argparse.ArgumentParser(prog='elbe remove_sign')
    parser.add_argument('file', help='file to unsign')

    args = parser.parse_args(argv)

    fname = unsign_file(args.file)
    if fname:
        print(f'unsigned file: {fname}')
    else:
        print('removing signature failed')
