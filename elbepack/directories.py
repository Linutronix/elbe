# ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (C) 2015  Linutronix GmbH
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

import elbepack
import os
from pkgutil import iter_modules

elbe_exe = None

def init_directories(elbe_relpath):
    global elbe_exe
    elbe_exe = os.path.abspath(elbe_relpath)

def get_cmdlist():
    return [ x for _, x, _ in iter_modules(elbepack.commands.__path__) ]

pack_dir = elbepack.__path__[0]
init_template_dir = os.path.join( pack_dir, "init" )
mako_template_dir = os.path.join( pack_dir, "mako" )

default_preseed = etree( os.path.join( pack_dir, "default-preseed.xml" ) )

