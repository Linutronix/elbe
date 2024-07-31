# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2017 Linutronix GmbH

import argparse
import os
import sys

from elbepack.xmlpreprocess import XMLPreprocessError, xmlpreprocess


def _add_arguments(parser):
    parser.add_argument('-v', '--variants',
                        type=lambda v: v.split(','),
                        help='enable only tags with empty or given variant')
    parser.add_argument('-p', '--proxy', help='add proxy to mirrors')
    parser.add_argument('-z', '--gzip', type=int, default=9,
                        help='gzip compression level 1-9 (0: no compression)')


def add_xmlpreprocess_passthrough_arguments(parser):
    group = parser.add_argument_group('Elbe preprocess options',
                                      'Options passed through to invocation of "elbe preprocess"')
    _add_arguments(group)


def run_command(argv):
    aparser = argparse.ArgumentParser(prog='elbe preprocess')
    aparser.add_argument('-o', '--output', default='preprocess.xml',
                         help='preprocessed output file')
    aparser.add_argument('xmlfile')
    _add_arguments(aparser)
    args = aparser.parse_args(argv)

    if not os.path.isfile(args.xmlfile):
        print(f"{args[0]} doesn't exist", file=sys.stderr)
        sys.exit(113)

    try:
        xmlpreprocess(args.xmlfile, args.output,
                      variants=args.variants, proxy=args.proxy, gzip=args.gzip)
    except XMLPreprocessError as e:
        print(e, file=sys.stderr)
        sys.exit(114)
