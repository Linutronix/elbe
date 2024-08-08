# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2016-2018 Linutronix GmbH

import os

from elbepack.cli import add_argument


def add_argument_soaptimeout(parser_or_func):
    return add_argument(
        parser_or_func,
        '--soaptimeout',
        type=int,
        default=os.environ.get('ELBE_SOAPTIMEOUT_SECS', '90'),
    )


def add_argument_soapport(parser_or_func, arg='--port'):
    return add_argument(
        parser_or_func,
        arg,
        dest='soapport',
        type=int,
        default=os.environ.get('ELBE_SOAPPORT', '7587'),
    )


def add_arguments_soapclient(parser_or_func):
    parser_or_func = add_argument(
        parser_or_func,
        '--host',
        dest='soaphost',
        default=os.environ.get('ELBE_SOAPHOST', 'localhost'),
    )
    parser_or_func = add_argument_soapport(parser_or_func)
    parser_or_func = add_argument_soaptimeout(parser_or_func)

    parser_or_func = add_argument(
        parser_or_func,
        '--user',
        dest='soapuser',
        default=os.environ.get('ELBE_USER', 'root'),
    )

    parser_or_func = add_argument(
        parser_or_func,
        '--pass',
        dest='soappassword',
        default=os.environ.get('ELBE_USER', 'foo'),
    )

    parser_or_func = add_argument(
        parser_or_func,
        '--retries',
        dest='retries',
        type=int,
        default=10,
        help='How many times to retry the connection to the server before '
             'giving up (default is 10 times, yielding 10 seconds).')

    return parser_or_func


def add_argument_sshport(parser_or_func):
    return add_argument(
        parser_or_func,
        '--sshport',
        type=int,
        default=os.environ.get('ELBE_SSHPORT', '5022'),
    )
