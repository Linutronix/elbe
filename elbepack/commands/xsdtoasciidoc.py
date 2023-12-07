# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2013-2017 Linutronix GmbH

import sys

from optparse import OptionParser

from elbepack.treeutils import etree
from elbepack.directories import xsdtoasciidoc_mako_fname
from elbepack.templates import write_template


def run_command(argv):
    oparser = OptionParser(
        usage='usage: %prog xsdtoasciidoc [options] <xsdfile>')

    oparser.add_option('--output', dest='out',
                       help='specify output filename',
                       metavar='FILE')

    (opt, args) = oparser.parse_args(argv)

    if len(args) != 1:
        print('Wrong number of arguments')
        oparser.print_help()
        sys.exit(90)

    xml = etree(args[0])

    if not opt.out:
        print('--output is mandatory')
        sys.exit(91)

    d = {'opt': opt,
         'xml': xml}

    write_template(opt.out, xsdtoasciidoc_mako_fname, d)
