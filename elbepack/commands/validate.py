# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2013-2017 Linutronix GmbH

import argparse
import os
import sys

from elbepack.elbexml import ElbeXML, ValidationError, ValidationMode
from elbepack.validate import validate_xml


def run_command(argv):
    aparser = argparse.ArgumentParser(prog='elbe validate')
    aparser.add_argument('--validate-urls', dest='validate_urls',
                         help='try to access specified repositories',
                         default=False, action='store_true')
    aparser.add_argument('xmlfile')

    args = aparser.parse_args(argv)

    if not os.path.exists(args.xmlfile):
        print(f'{args.xmlfile} - file not found')
        aparser.print_help()
        sys.exit(59)

    validation = validate_xml(args.xmlfile)
    if validation:
        print('validation failed')
        for i in validation:
            print(i)
        sys.exit(60)

    if args.validate_urls:
        try:
            ElbeXML(args.xmlfile, url_validation=ValidationMode.CHECK_ALL)
        except ValidationError as e:
            print(e)
            sys.exit(61)
