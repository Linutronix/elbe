# ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (c) 2013, 2015, 2017 Manuel Traut <manut@linutronix.de>
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import print_function

import sys
import os

from optparse import OptionParser

from elbepack.archivedir import chg_archive
from elbepack.treeutils import etree

def run_command(argv):

    oparser = OptionParser(
        usage="usage: %prog chg_archive [options] <xmlfile> "
              "[<archive>|<directory>]")
    oparser.add_option(
        "--keep-attributes",
        action="store_true",
        help="keep file owners and groups, if not specified all files will "
             "belong to root:root",
        dest="keep_attributes",
        default=False)

    (opt, args) = oparser.parse_args(argv)

    if len(args) != 2:
        print("Wrong number of arguments")
        oparser.print_help()
        sys.exit(20)

    try:
        xml = etree(args[0])
    except BaseException:
        print("Error reading xml file!")
        sys.exit(20)

    try:
        xml = chg_archive(xml, args[1], opt.keep_attributes)
    except BaseException:
        print("Error reading archive")
        sys.exit(20)

    try:
        xml.write(args[0])
    except BaseException:
        print("Unable to write new xml file")
        sys.exit(20)
