# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2014-2015, 2017 Linutronix GmbH

import argparse

from elbepack.egpg import sign_file


def run_command(argv):
    parser = argparse.ArgumentParser(prog='elbe sign')
    parser.add_argument('file', help='file to sign')
    parser.add_argument('fingerprint', help='valid gnupg fingerprint')

    args = parser.parse_args(argv)

    sign_file(args.file, args.fingerprint)
