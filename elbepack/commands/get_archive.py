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

import os
import sys

from base64 import standard_b64decode

from elbepack.treeutils import etree
from optparse import OptionParser


def unbase(s, fname):
    outfile = file(fname, "w")
    outfile.write(standard_b64decode(s))
    outfile.close()


def run_command(argv):

    oparser = OptionParser(
        usage="usage: %prog get_archive <xmlfile> <archive>")
    (opt, args) = oparser.parse_args(argv)

    if len(args) != 2:
        print("Wrong number of arguments")
        oparser.print_help()
        sys.exit(20)

    if os.path.exists(args[1]):
        print("archive already exists, bailing out")
        sys.exit(20)

    try:
        xml = etree(args[0])
    except BaseException:
        print("Error reading xml file!")
        sys.exit(20)

    if xml.has("archive") and not xml.text("archive") is None:
        try:
            unbase(xml.text("archive"), args[1])
        except BaseException:
            print("Error writing archive")
            sys.exit(20)
    else:
        print("no archive in this xml file.")
        sys.exit(20)
