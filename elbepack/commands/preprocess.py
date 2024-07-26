# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2017 Linutronix GmbH

import argparse
import os
import sys
from optparse import OptionGroup

from elbepack.xmlpreprocess import XMLPreprocessError, xmlpreprocess


def _comma_separated_list(option, opt, value, parser):
    if value is None:
        return

    setattr(parser.values, option.dest, value.split(','))


def _add_options(oparser):
    oparser.add_option('-v', '--variants', dest='variants',
                       action='callback', callback=_comma_separated_list, type=str,
                       help='enable only tags with empty or given variant')

    oparser.add_option('-p', '--proxy', dest='proxy',
                       default=None,
                       help='add proxy to mirrors')

    oparser.add_option('-z', '--gzip', dest='gzip', type='int',
                       default=9,
                       help='gzip compression level 1-9 (0: no compression)')


def add_xmlpreprocess_passthrough_options(oparser):
    group = OptionGroup(oparser,
                        'Elbe preprocess options',
                        'Options passed through to invocation of '
                        '"elbe preprocess"')
    _add_options(group)
    oparser.add_option_group(group)


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
        xmlpreprocess(args.xmlfile, args.output, args.variants, args.proxy, args.gzip)
    except XMLPreprocessError as e:
        print(e, file=sys.stderr)
        sys.exit(114)
