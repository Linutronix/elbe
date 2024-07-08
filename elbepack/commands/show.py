# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2013-2015, 2017 Linutronix GmbH

import argparse
import sys

from elbepack.treeutils import etree
from elbepack.validate import validate_xml


def run_command(argv):

    aparser = argparse.ArgumentParser(prog='elbe show')

    aparser.add_argument('--verbose', action='store_true', dest='verbose',
                         default=False,
                         help='show detailed project informations')

    aparser.add_argument('--skip-validation', action='store_true',
                         dest='skip_validation', default=False,
                         help='Skip xml schema validation')

    aparser.add_argument('xmlfile')

    args = aparser.parse_args(argv)

    try:
        if not args.skip_validation:
            validation = validate_xml(args.xmlfile)
            if validation:
                print('xml validation failed. Bailing out')
                for i in validation:
                    print(i)
                sys.exit(109)

        xml = etree(args.xmlfile)
    except BaseException:
        print('Unable to open xml File. Bailing out')
        sys.exit(110)

    if not xml.has('./project'):
        print('no project description available')
        sys.exit(111)

    print(f'== {args.xmlfile} ==')
    print(f"Debian suite: {xml.text('./project/suite')}")
    for s in xml.text('./project/description').splitlines():
        print(f'{s.strip()}')
    if args.verbose:
        if xml.has('./target/passwd'):
            print(f"root password: {xml.text('./target/passwd')}")
        print(
            'primary_mirror: '
            f"{xml.text('./project/mirror/primary_proto')}://"
            f"{xml.text('./project/mirror/primary_host')}"
            f"{xml.text('./project/mirror/primary_path')}")
        if xml.has('./project/mirror/url-list'):
            print('additional mirrors:')
            for url in xml.node('./project/mirror/url-list'):
                if url.has('binary'):
                    print(f"    deb {url.text('binary').strip()}")
                if url.has('source'):
                    print(f"    deb-src {url.text('source').strip()}")
        if xml.has('./target/pkg-list'):
            print('packages:')
            for pkg in xml.node('./target/pkg-list'):
                print(f'    {pkg.et.text}')
        print(f"skip package validation: {xml.has('./project/noauth')}")
        print(f"archive embedded?        {xml.has('./archive')}")
