# ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (c) 2016-2017 Manuel Traut <manut@linutronix.de>
#
# SPDX-License-Identifier: GPL-3.0-or-later

import sys

from optparse import OptionParser

from elbepack.elbexml import ElbeXML, ValidationError

def run_command(argv):

    oparser = OptionParser(
        usage="usage: %prog add [options] <xmlfile> <pkg1> [pkgN]")
    (_, args) = oparser.parse_args(argv)

    if len(args) < 2:
        print("Wrong number of arguments")
        oparser.print_help()
        sys.exit(20)

    xmlfile = args[0]
    pkg_lst = args[1:]

    try:
        xml = ElbeXML(xmlfile)
    except ValidationError as E:
        print(f"Error while reading xml file {xmlfile}: {E}")
        sys.exit(20)

    for pkg in pkg_lst:
        try:
            xml.add_target_package(pkg)
        except ValueError as E:
            print(f"Error while adding package {pkg} to {xmlfile}: {E}")
            sys.exit(20)

    try:
        xml.xml.write(xmlfile)
        sys.exit(0)
    except PermissionError as E:
        print(f"Unable to truncate file {xmlfile}: {E}")

    sys.exit(20)
