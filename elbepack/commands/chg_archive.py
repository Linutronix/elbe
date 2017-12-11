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

from __future__ import print_function

import sys
import os

from base64 import standard_b64encode

from elbepack.treeutils import etree
from optparse import OptionParser


def enbase( fname ):
    infile = file(fname, "r")
    s = infile.read()
    enc = standard_b64encode(s)

    splited = ""
    i=0
    l_enc = len(enc)
    while i<l_enc:
        splited += (enc[i:i+60]+"\n")
        i+=60

    return splited

def run_command( argv ):

    oparser = OptionParser( usage="usage: %prog chg_archive [options] <xmlfile> [<archive>|<directory>]")
    oparser.add_option ("--keep-attributes", action="store_true",
                        help="keep file owners and groups, if not specified all files will belong to root:root",
                        dest="keep_attributes", default=False)

    (opt,args) = oparser.parse_args(argv)

    if len(args) != 2:
        print("Wrong number of arguments")
        oparser.print_help()
        sys.exit(20)

    try:
        xml = etree( args[0] )
    except:
        print("Error reading xml file!")
        sys.exit(20)

    if os.path.isdir (args[1]):
        archive = '.archive.tbz'
        if opt.keep_attributes:
            cmd = 'tar cfj .archive.tbz -C '
        else:
            cmd = 'tar cjf .archive.tbz --owner=root --group=root -C '
        cmd += args[1] + ' .'
        os.system (cmd)
    else:
        archive = args[1]

    try:
        arch = xml.ensure_child( "archive" )
        arch.set_text( enbase( archive ) )
    except:
        print("Error reading archive")
        sys.exit(20)

    try:
        xml.write( args[0] )
    except:
        print("Unable to write new xml file")
        sys.exit(20)

    if os.path.isdir (args[1]):
        os.remove (archive)
