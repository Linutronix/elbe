#!/usr/bin/env python
#
# ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (C) 2013  Linutronix GmbH
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

import sys

from elbepack.treeutils import etree
from optparse import OptionParser


def run_command( argv ):

    oparser = OptionParser( usage="usage: %prog setcdrom <xmlfile> <cdrom>")
    (opt,args) = oparser.parse_args(argv)

    if len(args) != 2:
        print "Wrong number of arguments"
        oparser.print_help()
        sys.exit(20)

    try:
        xml = etree( args[0] )
    except:
        print "Error reading xml file!"
        sys.exit(20)


    mirror = xml.node("project/mirror")
    mirror.clear()
    cdrom = mirror.ensure_child("cdrom")
    cdrom.set_text( args[1] )

    try:
        xml.write( args[0] )
    except:
        print "Unable to write new xml file"
        sys.exit(20)


