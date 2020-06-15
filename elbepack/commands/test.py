# ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (c) 2020 Olivier Dion <dion@linutronix.de>
#
# SPDX-License-Identifier: GPL-3.0-or-later

# elbepack/commands/test.py - Elbe unit test wrapper

import os

from elbepack.shellhelper import system

def run_command(argv):
    this_dir = os.path.dirname(os.path.realpath(__file__))
    top_dir  = os.path.join(this_dir, "..", "..")
    system("python3 -m unittest discover --start-directory '%s' %s" %
           (top_dir, " ".join(argv)), allow_fail=True)
