# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2015-2017 Linutronix GmbH

import argparse
import datetime
import os

from elbepack.cli import add_arguments_from_decorated_function, add_deprecated_argparse_argument
from elbepack.commands.preprocess import add_xmlpreprocess_passthrough_arguments
from elbepack.initvmaction import initvm_actions


def run_command(argv):
    aparser = argparse.ArgumentParser(prog='elbe initvm')

    # Various callers specify this argument at the global 'elbe initvm' level.
    # Remove this at some point.
    aparser.add_argument('--output', dest='global_outdir',
                         type=os.path.abspath,
                         help=argparse.SUPPRESS)

    add_deprecated_argparse_argument(aparser, '--nesting')
    add_deprecated_argparse_argument(aparser, '--devel')

    add_xmlpreprocess_passthrough_arguments(aparser)

    subparsers = aparser.add_subparsers(required=True)

    for action_name, do_action in initvm_actions.items():
        action_parser = subparsers.add_parser(action_name)
        action_parser.set_defaults(func=do_action)
        add_arguments_from_decorated_function(action_parser, do_action)

    args = aparser.parse_args(argv)
    args.parser = aparser

    if args.global_outdir is not None:
        if not hasattr(args, 'outdir'):
            aparser.error('unrecognized arguments: --output')
        if args.outdir is not None:
            aparser.error('Only one --output can be specified')

        args.outdir = args.global_outdir

    if hasattr(args, 'outdir') and args.outdir is None:
        args.outdir = os.path.abspath(
            'elbe-build-' + datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
        )

    args.func(args)
