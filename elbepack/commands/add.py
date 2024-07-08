# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2016-2017 Linutronix GmbH

import argparse
import sys

from elbepack.elbexml import ElbeXML, ValidationError


def run_command(argv):

    aparser = argparse.ArgumentParser(prog='elbe add')
    aparser.add_argument('xmlfile')
    aparser.add_argument('pkg', nargs='+')

    args = aparser.parse_args(argv)

    xmlfile = args.xmlfile
    pkg_lst = args.pkg

    try:
        xml = ElbeXML(xmlfile)
    except ValidationError as E:
        print(f'Error while reading xml file {xmlfile}: {E}')
        sys.exit(87)

    for pkg in pkg_lst:
        try:
            xml.add_target_package(pkg)
        except ValueError as E:
            print(f'Error while adding package {pkg} to {xmlfile}: {E}')
            sys.exit(88)

    try:
        xml.xml.write(xmlfile)
        sys.exit(0)
    except PermissionError as E:
        print(f'Unable to truncate file {xmlfile}: {E}')

    sys.exit(89)
