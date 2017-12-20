# ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (c) 2013, 2015, 2017 Manuel Traut <manut@linutronix.de>
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import print_function

import sys
import os

from base64 import standard_b64encode

from elbepack.treeutils import etree
from optparse import OptionParser


def enbase(fname):
    infile = file(fname, "r")
    s = infile.read()
    enc = standard_b64encode(s)

    splited = ""
    i = 0
    l_enc = len(enc)
    while i < l_enc:
        splited += (enc[i:i + 60] + "\n")
        i += 60

    return splited


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

    if os.path.isdir(args[1]):
        archive = '.archive.tbz'
        if opt.keep_attributes:
            cmd = 'tar cfj .archive.tbz -C '
        else:
            cmd = 'tar cjf .archive.tbz --owner=root --group=root -C '
        cmd += args[1] + ' .'
        os.system(cmd)
    else:
        archive = args[1]

    try:
        arch = xml.ensure_child("archive")
        arch.set_text(enbase(archive))
    except BaseException:
        print("Error reading archive")
        sys.exit(20)

    try:
        xml.write(args[0])
    except BaseException:
        print("Unable to write new xml file")
        sys.exit(20)

    if os.path.isdir(args[1]):
        os.remove(archive)
