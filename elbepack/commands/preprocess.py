# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2017 Linutronix GmbH

import sys
import os
from optparse import OptionParser
from elbepack.xmlpreprocess import XMLPreprocessError, xmlpreprocess


def add_pass_through_options(oparser):
    oparser.add_option("-v", "--variants", dest="variant",
                       default=None,
                       help="enable only tags with empty or given variant")

    oparser.add_option("-p", "--proxy", dest="proxy",
                       default=None,
                       help="add proxy to mirrors")

    oparser.add_option("-z", "--gzip", dest="gzip", type="int",
                       default=9,
                       help="gzip compression level 1-9 (0: no compression)")

def run_command(argv):
    oparser = OptionParser(usage="usage: %prog preprocess [options] <xmlfile>")
    oparser.add_option("-o", "--output", dest="output",
                       default="preprocess.xml",
                       help="preprocessed output file", metavar="<xmlfile>")
    add_pass_through_options(oparser)
    (opt, args) = oparser.parse_args(argv)

    if len(args) != 1:
        print("Wrong number of arguments", file=sys.stderr)
        oparser.print_help()
        sys.exit(20)

    if not os.path.isfile(args[0]):
        print(f"{args[0]} doesn't exist", file=sys.stderr)
        sys.exit(20)

    variants = []
    if opt.variant:
        variants = opt.variant.split(',')

    try:
        xmlpreprocess(args[0], opt.output, variants, opt.proxy, opt.gzip)
    except XMLPreprocessError as e:
        print(e, file=sys.stderr)
        sys.exit(20)
