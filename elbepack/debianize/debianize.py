# ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (c) 2016-2017 Manuel Traut <manut@linutronix.de>
#
# SPDX-License-Identifier: GPL-3.0-or-later

from npyscreen import NPSAppManaged

# don't remove these imports; even if pylint, etc believes they are unused
from elbepack.debianize.kernel import Kernel
from elbepack.debianize.uboot import UBoot
from elbepack.debianize.barebox import BareBox

from elbepack.debianize.base import DebianizeBase


class Debianize (NPSAppManaged):
    def __init__(self, debianizer):
        self.debianizer = debianizer
        NPSAppManaged.__init__(self)

    def onStart(self):
        self.registerForm('MAIN', self.debianizer())
