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

from mako.template import Template
from mako import exceptions

import elbepack
from elbepack.treeutils import etree

from optparse import OptionParser

# Some more helpers
def template(fname, d):
    try:
        return Template(filename=fname).render(**d)
    except:
        print exceptions.text_error_template().render()
        raise

def write_template( outname, fname, d ):
    outfile = file(outname, "w")
    outfile.write( template( fname, d ) )
    outfile.close()

def run_command( argv ):
    pack_dir = elbepack.__path__[0]
    template_dir = os.path.join( pack_dir, "mako" )

    oparser = OptionParser(usage="usage: %prog xsdtoasciidoc [options] <xsdfile>")

    oparser.add_option( "--output", dest="out",
                        help="specify output filename",
                        metavar="FILE" )

    (opt,args) = oparser.parse_args(argv)

    if len(args) != 1:
        print "Wrong number of arguments"
        oparser.print_help()
        sys.exit(20)

    xml = etree( args[0] )

    if not opt.out:
        print 'output is mandatory'
        sys.exit(20)

    d = {"opt": opt,
         "xml": xml }

    write_template(opt.out, os.path.join(pack_dir, "xsdtoasciidoc.mako"), d )

