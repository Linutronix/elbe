# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2015, 2017 Linutronix GmbH

import os

import elbepack.main


def run_elbe_subcommand(args):
    return elbepack.main.main([
        'elbe', '--propagate-exception', *[os.fspath(arg) for arg in args],
    ])
