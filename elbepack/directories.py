# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2015, 2017 Linutronix GmbH

import subprocess
import sys
from pkgutil import iter_modules

import elbepack.commands


def get_cmdlist():
    return [x for _, x, _ in iter_modules(elbepack.commands.__path__)]


def run_elbe(args, **kwargs):
    return subprocess.run([sys.executable, '-melbepack', *args], **kwargs)
