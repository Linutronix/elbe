# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2024 Linutronix GmbH

import argparse
import optparse
import sys


def _deprecated_option_cb(option, opt, value, parser):
    print(f'Deprecated option "{option}" was used. This option is a NOOP.', file=sys.stderr)


def add_deprecated_optparse_option(oparser, *args, **kwargs):
    oparser.add_option(*args, **kwargs,
                       action='callback', callback=_deprecated_option_cb,
                       help=optparse.SUPPRESS_HELP)


class _DeprecatedArgumentAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string):
        print(f'Deprecated option "{option_string}" was used. This option is a NOOP.',
              file=sys.stderr)


def add_deprecated_argparse_argument(parser, *args, **kwargs):
    parser.add_argument(*args, **kwargs, action=_DeprecatedArgumentAction,
                        help=argparse.SUPPRESS)
