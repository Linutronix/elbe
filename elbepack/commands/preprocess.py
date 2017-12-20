# ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (c) 2017 Benedikt Spranger <b.spranger@linutronix.de>
# Copyright (c) 2017 Manuel Traut <manut@linutronix.de>
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import print_function

import sys
import os
from optparse import OptionParser
from elbepack.xmlpreprocess import XMLPreprocessError, xmlpreprocess


def run_command(argv):
    oparser = OptionParser(usage="usage: %prog preprocess [options] <xmlfile>")
    oparser.add_option("-o", "--output", dest="output",
                       default="preprocess.xml",
                       help="preprocessed output file", metavar="<xmlfile>")
    oparser.add_option("-v", "--variants", dest="variant",
                       default=None,
                       help="enable only tags with empty or given variant")
    (opt, args) = oparser.parse_args(argv)

    if len(args) != 1:
        print("Wrong number of arguments", file=sys.stderr)
        oparser.print_help()
        sys.exit(20)

    if not os.path.isfile(args[0]):
        print("%s doesn't exist" % args[0], file=sys.stderr)
        sys.exit(20)

    variants = []
    if opt.variant:
        variants = opt.variant.split(',')

    try:
        xmlpreprocess(args[0], opt.output, variants)
    except XMLPreprocessError as e:
        print(e, file=sys.stderr)
        sys.exit(20)
