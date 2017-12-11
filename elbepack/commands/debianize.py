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

from __future__ import print_function

import os
import sys

from elbepack.debianize.debianize import Debianize, DebianizeBase

def run_command ( args ):
    if os.path.exists ('debian'):
        print("debian folder already exists, nothing to do")
        sys.exit (10)

    try:
        debianizer = DebianizeBase.get_debianizer ()
        Debianize (debianizer).run ()
        sys.exit(10)
    except KeyError:
        print("This creates a debinization of a source directory.")
        print("The software was not able to identify the current directory.")
        print("Please run the command from source directory")
        sys.exit (20)
