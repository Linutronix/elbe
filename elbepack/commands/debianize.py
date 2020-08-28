# ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (c) 2016-2017 Manuel Traut <manut@linutronix.de>
# Copyright (c) 2017 Torben Hohn <torben.hohn@linutronix.de>
#
# SPDX-License-Identifier: GPL-3.0-or-later

import os
import sys

from elbepack.debianize.base.tui import TUI
from elbepack.debianize.panels.factory import detect_panel


def run_command(_args):

    if os.path.exists('debian'):
        print("debian folder already exists, nothing to do")
        sys.exit(10)
    try:
        TUI(detect_panel())()
    except KeyError:
        print("This creates a debianization of a source directory.\n"
              "The software was not able to identify the current directory.\n"
              "Please run the command from a valid source directory")
        sys.exit(20)
