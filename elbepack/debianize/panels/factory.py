# ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (c) 2019 Olivier Dion <dion@linutronix.de>
#
# SPDX-License-Identifier: GPL-3.0-or-later


import os

from elbepack.debianize.panels.uboot import UBoot
from elbepack.debianize.panels.kernel import Kernel
from elbepack.debianize.panels.barebox import BareBox


panels = [
    UBoot,
    Kernel,
    BareBox
]


def detect_panel():
    for panel in panels:
        match = True
        for f in panel.match_files:
            if not os.path.exists(f):
                match = False
                break
        if match:
            return panel()

    raise KeyError
