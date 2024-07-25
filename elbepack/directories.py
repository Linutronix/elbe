# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2015, 2017 Linutronix GmbH

import os
import subprocess
import sys

import elbepack.main


def run_elbe(args, **kwargs):
    return subprocess.run([sys.executable, '-melbepack', *args], **kwargs)


def run_elbe_subcommand(args):
    return elbepack.main.main([
        'elbe', *[os.fspath(arg) for arg in args],
    ])
