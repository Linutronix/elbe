# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2013, 2017 Linutronix GmbH

import argparse
import os
import sys
from base64 import standard_b64decode

from elbepack.treeutils import etree


def unbase(s, fname):
    outfile = open(fname, 'w+b')
    outfile.write(standard_b64decode(s))
    outfile.close()


def run_command(argv):

    aparser = argparse.ArgumentParser(prog='elbe get_archive')
    aparser.add_argument('xmlfile')
    aparser.add_argument('archive')

    args = aparser.parse_args(argv)

    if os.path.exists(args.archive):
        print('archive already exists, bailing out')
        sys.exit(102)

    try:
        xml = etree(args.xmlfile)
    except BaseException:
        print('Error reading xml file!')
        sys.exit(103)

    if xml.has('archive') and not xml.text('archive') is None:
        try:
            unbase(xml.text('archive'), args.archive)
        except BaseException:
            print('Error writing archive')
            sys.exit(104)
    else:
        print('no archive in this xml file.')
        sys.exit(105)
