# ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (c) 2013, 2017 Manuel Traut <manut@linutronix.de>
# Copyright (c) 2014 Torben Hohn <torbenh@linutronix.de>
#
# SPDX-License-Identifier: GPL-3.0-or-later

import sys

from optparse import OptionParser

from elbepack.treeutils import etree


def parse_selections(fname):
    fp = open(fname, "r")

    sels = []

    for l in fp.readlines():
        if not l:
            continue
        if l[0] == '#':
            continue

        sp = l.split()

        print(f"{sp[0]} {sp[1]}")

        if sp[1] == 'install':
            sels.append(sp[0])

    print(sels)
    return sels


def run_command(argv):

    oparser = OptionParser(usage="usage: %prog setsel <xmlfile> <pkglist.txt>")
    (_, args) = oparser.parse_args(argv)

    if len(args) != 2:
        print("Wrong number of arguments")
        oparser.print_help()
        sys.exit(20)

    xml = etree(args[0])

    pkg_list = xml.node("/pkg-list")

    pkg_list.clear()

    sels = parse_selections(args[1])

    for s in sels:
        new = pkg_list.append('pkg')
        new.set_text(s)

    xml.write(args[0])
