# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2016-2018 Linutronix GmbH

import os

from elbepack.cli import add_argument


def add_argument_soaptimeout(parser):
    parser.add_argument(
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


def add_arguments_soapclient(parser):
    parser.add_argument(
        '--host',
        dest='soaphost',
        default=os.environ.get('ELBE_SOAPHOST', 'localhost'),
    )
    add_argument_soapport(parser)
    add_argument_soaptimeout(parser)

    parser.add_argument(
        '--user',
        dest='soapuser',
        default=os.environ.get('ELBE_USER', 'root'),
    )

    parser.add_argument(
        '--pass',
        dest='soappassword',
        default=os.environ.get('ELBE_USER', 'foo'),
    )

    parser.add_argument(
        '--retries',
        dest='retries',
        type=int,
        default=10,
        help='How many times to retry the connection to the server before '
             'giving up (default is 10 times, yielding 10 seconds).')


def add_argument_sshport(parser_or_func):
    return add_argument(
        parser_or_func,
        '--sshport',
        type=int,
        default=os.environ.get('ELBE_SSHPORT', '5022'),
    )
