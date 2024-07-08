# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2022 Linutronix GmbH

import argparse
import os
import sys
from threading import Event

from elbepack.repodir import Repodir, RepodirError


def run_command(argv):
    aparser = argparse.ArgumentParser(prog='elbe repodir')
    aparser.add_argument('-o', '--output', dest='output',
                         default='repodir.xml',
                         help='preprocessed output file', metavar='<xmlfile>')
    aparser.add_argument('xmlfile')
    args = aparser.parse_args(argv)

    xml_input = args.xmlfile
    if not os.path.isfile(xml_input):
        print(f'{xml_input} does not exist', file=sys.stderr)
        sys.exit(56)

    if os.path.exists(args.output):
        # This will be overridden. Try to delete first to make sure it is a regular file.
        os.remove(args.output)

    try:
        with Repodir(xml_input, args.output):
            Event().wait()
    except KeyboardInterrupt:
        print()
    except RepodirError as e:
        print(e, file=sys.stderr)
        sys.exit(57)
