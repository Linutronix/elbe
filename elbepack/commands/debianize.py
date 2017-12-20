# ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (c) 2016-2017 Manuel Traut <manut@linutronix.de>
# Copyright (c) 2017 Torben Hohn <torben.hohn@linutronix.de>
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import print_function

import os
import sys

from elbepack.debianize.debianize import Debianize, DebianizeBase


def run_command(args):
    if os.path.exists('debian'):
        print("debian folder already exists, nothing to do")
        sys.exit(10)

    try:
        debianizer = DebianizeBase.get_debianizer()
        Debianize(debianizer).run()
        sys.exit(10)
    except KeyError:
        print("This creates a debinization of a source directory.")
        print("The software was not able to identify the current directory.")
        print("Please run the command from source directory")
        sys.exit(20)
