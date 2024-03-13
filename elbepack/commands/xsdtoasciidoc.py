# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2013-2017 Linutronix GmbH

import importlib.resources
import sys
from optparse import OptionParser

import elbepack
from elbepack.templates import write_template
from elbepack.treeutils import etree


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

    template = importlib.resources.files(elbepack) / 'xsdtoasciidoc.mako'
    write_template(opt.out, template, d)
