# ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (C) 2017  Linutronix GmbH
#
# This file is part of ELBE.
#
# ELBE is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# ELBE is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with ELBE.  If not, see <http://www.gnu.org/licenses/>.

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
