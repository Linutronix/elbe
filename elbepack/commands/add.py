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

import sys

from elbepack.elbexml import ElbeXML
from optparse import OptionParser

def run_command( argv ):

    oparser = OptionParser( usage="usage: %prog add [options] <xmlfile> <pkg1> [pkgN]")
    (opt,args) = oparser.parse_args(argv)

    if len(args) < 2:
        print("Wrong number of arguments")
        oparser.print_help()
        sys.exit(20)

    try:
        xml = ElbeXML ( args[0] )
    except Exception as e:
        print(("Error reading xml file: %s" % str(e)))
        sys.exit(20)

    for a in args[1:]:
        try:
            xml.add_target_package( a )
        except Exception as e:
            print(("Error adding package %s: %s" % (a, str(e))))
            sys.exit(20)

    try:
        xml.xml.write( args[0] )
    except:
        print("Unable to write new xml file")
        sys.exit(20)
