#!/usr/bin/env python
#
# ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (C) 2016  Linutronix GmbH
#
# This file is part of ELBE.
#
# ELBE is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# ELBE is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with ELBE.  If not, see <http://www.gnu.org/licenses/>.

import os
import sys

from npyscreen import NPSAppManaged, FormMultiPage
from npyscreen import TitleText, TitleSelectOne, ButtonPress

from shutil import copyfile

##############################################################################
#TODO before adding another helper, refactor the code to be 'plugin-like',
# see finetuning for example.

from elbepack.debianize.kernel import Kernel
from elbepack.debianize.uboot  import UBoot
debianizer = {'kernel': Kernel,
              'uboot':  UBoot}

files = {'kernel': ['Kbuild', 'Kconfig', 'MAINTAINERS', 'REPORTING-BUGS'],
         'uboot':  ['Kbuild', 'Kconfig', 'MAINTAINERS', 'config.mk'],}
##############################################################################

class Debianize (NPSAppManaged):
    def __init__ (self, debianizer):
        self.debianizer = debianizer
        NPSAppManaged.__init__ (self)

    def onStart (self):
        self.registerForm('MAIN', self.debianizer ())
