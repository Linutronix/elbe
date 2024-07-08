# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2016-2017 Linutronix GmbH

import argparse
import sys

from elbepack.treeutils import etree
from elbepack.validate import validate_xml


def run_command(argv):

    aparser = argparse.ArgumentParser(prog='elbe pin_versions')
    aparser.add_argument('--skip-validation', action='store_true',
                         dest='skip_validation', default=False,
                         help='Skip xml schema validation')
    aparser.add_argument('xmlfile')

    args = aparser.parse_args(argv)

    if not args.skip_validation:
        validation = validate_xml(args.xmlfile)
        if validation:
            print('xml validation failed. Bailing out')
            for i in validation:
                print(i)
            sys.exit(95)

    try:
        xml = etree(args.xmlfile)
    except BaseException:
        print('Error reading xml file!')
        sys.exit(96)

    if not xml.has('fullpkgs'):
        print('xml file does not have fullpkgs node')
        sys.exit(97)

    plist = xml.ensure_child('/target/pkg-list')
    plist.clear()

    fullp = xml.node('fullpkgs')

    for p in fullp:
        pname = p.et.text
        pver = p.et.get('version')

        pak = plist.append('pkg')
        pak.set_text(pname)
        pak.et.tail = '\n'
        pak.et.set('version', pver)

    try:
        xml.write(args.xmlfile)
    except BaseException:
        print('Unable to write new xml file')
        sys.exit(98)
