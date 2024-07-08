# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2013, 2015, 2017 Linutronix GmbH

import argparse
import sys

from elbepack.archivedir import chg_archive
from elbepack.treeutils import etree


def run_command(argv):

    aparser = argparse.ArgumentParser(prog='elbe chg_archive')
    aparser.add_argument(
        '--keep-attributes',
        action='store_true',
        help='keep file owners and groups, if not specified all files will '
             'belong to root:root',
        dest='keep_attributes',
        default=False)
    aparser.add_argument('xmlfile')
    aparser.add_argument('archive', metavar='[archive.tar.bz2 | directory]')

    args = aparser.parse_args(argv)

    try:
        xml = etree(args.xmlfile)
    except BaseException:
        print('Error reading xml file!')
        sys.exit(43)

    try:
        xml = chg_archive(xml, args.archive, args.keep_attributes)
    except BaseException:
        print('Error reading archive')
        sys.exit(44)

    try:
        xml.write(args.xmlfile)
    except BaseException:
        print('Unable to write new xml file')
        sys.exit(45)
