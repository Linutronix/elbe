# ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (c) 2013, 2017 Manuel Traut <manut@linutronix.de>
# Copyright (c) 2017 John Ogness <john.ogness@linutronix.de>
#
# SPDX-License-Identifier: GPL-3.0-or-later

import os
import sys

from base64 import standard_b64decode
from optparse import OptionParser

from elbepack.treeutils import etree


def unbase(s, fname):
    outfile = open(fname, "w+b")
    outfile.write(standard_b64decode(s))
    outfile.close()


def run_command(argv):

    oparser = OptionParser(
        usage="usage: %prog get_archive <xmlfile> <archive>")
    (_, args) = oparser.parse_args(argv)

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
