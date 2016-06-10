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

from npyscreen import TitleText, TitleSelectOne

from shutil import copyfile

from elbepack.directories import mako_template_dir
from elbepack.debianize.base import DebianizeBase, template

# this is just a template to show how debianizing another component should work

class UBoot (DebianizeBase):
    def __init__ (self):
        print ("debianization of uboot is not supported at the moment")
        sys.exit (-2)
        DebianizeBase.__init__ (self)

    def gui (self):
        pass

    def debianize (self):
        pass
