# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2022 Linutronix GmbH

import sys
import os
from optparse import OptionParser
from threading import Event

from elbepack.repodir import RepodirError, Repodir


def run_command(argv):
    oparser = OptionParser(usage="usage: %prog repodir [options] <xmlfile>")
    oparser.add_option("-o", "--output", dest="output",
                       default="repodir.xml",
                       help="preprocessed output file", metavar="<xmlfile>")
    (opt, args) = oparser.parse_args(argv)

    if len(args) != 1:
        print("Wrong number of arguments", file=sys.stderr)
        oparser.print_help()
        sys.exit(20)

    xml_input = args[0]
    if not os.path.isfile(xml_input):
        print(f"{xml_input} does not exist", file=sys.stderr)
        sys.exit(20)

    if os.path.exists(opt.output):
        # This will be overridden. Try to delete first to make sure it is a regular file.
        os.remove(opt.output)

    try:
        with Repodir(xml_input, opt.output):
            Event().wait()
    except KeyboardInterrupt:
        print()
    except RepodirError as e:
        print(e, file=sys.stderr)
        sys.exit(20)
