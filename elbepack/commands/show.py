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
from elbepack.validate import validate_xml

from optparse import OptionParser


def run_command(argv):
    oparser = OptionParser(usage="usage: %prog show [options] <filename>")

    oparser.add_option("--verbose", action="store_true", dest="verbose",
                       default=False,
                       help="show detailed project informations")

    oparser.add_option("--skip-validation", action="store_true",
                       dest="skip_validation", default=False,
                       help="Skip xml schema validation")

    (opt, args) = oparser.parse_args(argv)

    if len(args) == 0:
        print("No Filename specified")
        oparser.print_help()
        sys.exit(20)

    if len(args) > 1:
        print("too many filenames specified")
        oparser.print_help()
        sys.exit(20)

    try:
        if not opt.skip_validation:
            validation = validate_xml(args[0])
            if len(validation) != 0:
                print("xml validation failed. Bailing out")
                for i in validation:
                    print(i)
                sys.exit(20)

        xml = etree(args[0])
    except BaseException:
        print("Unable to open xml File. Bailing out")
        sys.exit(20)

    if not xml.has("./project"):
        print("no project description available")
        sys.exit(20)

    print("== %s ==" % (args[0]))
    print("Debian suite: %s" % (xml.text("./project/suite")))
    for s in xml.text("./project/description").splitlines():
        print("%s" % s.strip())
    if opt.verbose:
        print("root password: %s" % xml.text("./target/passwd"))
        print("primary_mirror: %s://%s%s" % (
              xml.text("./project/mirror/primary_proto"),
              xml.text("./project/mirror/primary_host"),
              xml.text("./project/mirror/primary_path")))
        if xml.has("./project/mirror/url-list"):
            print("additional mirrors:")
            for url in xml.node("./project/mirror/url-list"):
                if url.has("binary"):
                    print("    deb %s" % url.text("binary").strip())
                if url.has("source"):
                    print("    deb-src %s" % url.text("source").strip())
        print("packages:")
        for pkg in xml.node("./target/pkg-list"):
            print("    %s" % pkg.et.text)
        print("skip package validation: %s" % xml.has("./project/noauth"))
        print("archive embedded?        %s" % xml.has("./archive"))
