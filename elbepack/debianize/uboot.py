# ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (c) 2016-2017 Manuel Traut <manut@linutronix.de>
# Copyright (c) 2017 Torben Hohn <torben.hohn@linutronix.de>
#
# SPDX-License-Identifier: GPL-3.0-or-later

import sys

from elbepack.debianize.base import DebianizeBase

# this is just a template to show how debianizing another component should work


class UBoot (DebianizeBase):

    name = "uboot"
    files = ['Kbuild', 'Kconfig', 'MAINTAINERS', 'config.mk']

    def __init__(self):
        print("debianization of uboot is not supported at the moment")
        sys.exit(-2)
        DebianizeBase.__init__(self)

    def gui(self):
        pass

    def debianize(self):
        pass


DebianizeBase.register(UBoot)
