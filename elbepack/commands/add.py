# ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (c) 2016-2017 Manuel Traut <manut@linutronix.de>
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import print_function

import sys

from optparse import OptionParser

from elbepack.elbexml import ElbeXML

def run_command(argv):

    oparser = OptionParser(
        usage="usage: %prog add [options] <xmlfile> <pkg1> [pkgN]")
    (_, args) = oparser.parse_args(argv)

    if len(args) < 2:
        print("Wrong number of arguments")
        oparser.print_help()
        sys.exit(20)

    try:
        xml = ElbeXML(args[0])
    except Exception as e:
        print("Error reading xml file: %s" % str(e))
        sys.exit(20)

    for a in args[1:]:
        try:
            xml.add_target_package(a)
        except Exception as e:
            print("Error adding package %s: %s" % (a, str(e)))
            sys.exit(20)

    try:
        xml.xml.write(args[0])
    except BaseException:
        print("Unable to write new xml file")
        sys.exit(20)
