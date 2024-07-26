# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2015-2017 Linutronix GmbH

import argparse

from elbepack.cli import add_arguments_from_decorated_function
from elbepack.commands.preprocess import add_xmlpreprocess_passthrough_arguments
from elbepack.pbuilderaction import pbuilder_actions


def run_command(argv):
    aparser = argparse.ArgumentParser(prog='elbe pbuilder')

    add_xmlpreprocess_passthrough_arguments(aparser)

    subparsers = aparser.add_subparsers(required=True)

    for action_name, do_action in pbuilder_actions.items():
        action_parser = subparsers.add_parser(action_name)
        action_parser.set_defaults(func=do_action)
        add_arguments_from_decorated_function(action_parser, do_action)

    args = aparser.parse_args(argv)
    args.parser = aparser

    args.func(args)
