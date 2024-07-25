# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2014, 2017 Linutronix GmbH

import argparse

from elbepack.cli import add_arguments_from_decorated_function
from elbepack.dbaction import db_actions


def run_command(argv):
    aparser = argparse.ArgumentParser(prog='elbe db')
    subparsers = aparser.add_subparsers(required=True)

    for action_name, do_action in db_actions.items():
        action_parser = subparsers.add_parser(action_name)
        action_parser.set_defaults(func=do_action)
        add_arguments_from_decorated_function(action_parser, do_action)

    args = aparser.parse_args(argv)

    args.func(args)
