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

import os
import sys
import shutil


from elbepack.treeutils import etree
import urllib2
from optparse import OptionParser

def parse_selections( fname ):
    fp = file(fname,"r")

    sels = []

    for l in fp.readlines():
        if len(l) == 0:
            continue
        if l[0] == '#':
            continue

        sp = l.split()


        print sp[0], sp[1]

        if sp[1] == 'install':
            sels.append(sp[0])

    print sels
    return sels


def run_command( argv ):

    oparser = OptionParser(usage="usage: %prog setsel <xmlfile> <pkglist.txt>")
    (opt,args) = oparser.parse_args(argv)

    if len(args) != 2:
        print "Wrong number of arguments"
        oparser.print_help()
        sys.exit(20)

    xml = etree( args[0] )

    pkg_list = xml.node("/pkg-list")

    pkg_list.clear()

    sels = parse_selections( args[1] )

    for s in sels:
        new = pkg_list.append( 'pkg' )
        new.set_text( s )


    xml.write( args[0] )


