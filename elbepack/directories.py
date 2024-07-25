# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2015, 2017 Linutronix GmbH

import subprocess
import sys


def run_elbe(args, **kwargs):
    return subprocess.run([sys.executable, '-melbepack', *args], **kwargs)
