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
from optparse import OptionParser
from elbepack.validate import validate_xml


def run_command(argv):

    oparser = OptionParser(
        usage="usage: %prog pin_versions [options] <xmlfile>")
    oparser.add_option("--skip-validation", action="store_true",
                       dest="skip_validation", default=False,
                       help="Skip xml schema validation")

    (opt, args) = oparser.parse_args(argv)

    if len(args) != 1:
        print("Wrong number of arguments")
        oparser.print_help()
        sys.exit(20)

    if not opt.skip_validation:
        validation = validate_xml(args[0])
        if len(validation) != 0:
            print("xml validation failed. Bailing out")
            for i in validation:
                print(i)
            sys.exit(20)

    try:
        xml = etree(args[0])
    except BaseException:
        print("Error reading xml file!")
        sys.exit(20)

    if not xml.has("fullpkgs"):
        print("xml file does not have fullpkgs node")
        sys.exit(20)

    plist = xml.ensure_child("/target/pkg-list")
    plist.clear()

    fullp = xml.node("fullpkgs")

    for p in fullp:
        pname = p.et.text
        pver = p.et.get('version')

        pak = plist.append('pkg')
        pak.set_text(pname)
        pak.et.tail = '\n'
        pak.et.set('version', pver)

    try:
        xml.write(args[0])
    except BaseException:
        print("Unable to write new xml file")
        sys.exit(20)
