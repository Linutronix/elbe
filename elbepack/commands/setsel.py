# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2013-2014, 2017 Linutronix GmbH

import sys
from optparse import OptionParser

from elbepack.treeutils import etree


def parse_selections(fname):
    fp = open(fname, 'r')

    sels = []

    for lic in fp.readlines():
        if not lic:
            continue
        if lic[0] == '#':
            continue

        sp = lic.split()

        print(f'{sp[0]} {sp[1]}')

        if sp[1] == 'install':
            sels.append(sp[0])

    print(sels)
    return sels


def run_command(argv):

    oparser = OptionParser(usage='usage: %prog setsel <xmlfile> <pkglist.txt>')
    (_, args) = oparser.parse_args(argv)

    if len(args) != 2:
        print('Wrong number of arguments')
        oparser.print_help()
        sys.exit(23)

    xml = etree(args[0])

    pkg_list = xml.node('/pkg-list')

    pkg_list.clear()

    sels = parse_selections(args[1])

    for s in sels:
        new = pkg_list.append('pkg')
        new.set_text(s)

    xml.write(args[0])
