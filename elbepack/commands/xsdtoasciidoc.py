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

from elbepack.treeutils import etree
from elbepack.directories import xsdtoasciidoc_mako_fname
from elbepack.templates import write_template

from optparse import OptionParser


def run_command(argv):
    oparser = OptionParser(
        usage="usage: %prog xsdtoasciidoc [options] <xsdfile>")

    oparser.add_option("--output", dest="out",
                       help="specify output filename",
                       metavar="FILE")

    (opt, args) = oparser.parse_args(argv)

    if len(args) != 1:
        print("Wrong number of arguments")
        oparser.print_help()
        sys.exit(20)

    xml = etree(args[0])

    if not opt.out:
        print("--output is mandatory")
        sys.exit(20)

    d = {"opt": opt,
         "xml": xml}

    write_template(opt.out, xsdtoasciidoc_mako_fname, d)
