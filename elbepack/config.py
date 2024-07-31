# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2016-2018 Linutronix GmbH

import os

from elbepack.cli import add_argument_to_parser_or_function


class Config(dict):
    def __init__(self):
        dict.__init__(self)
        self['soaphost'] = 'localhost'
        self['soapport'] = '7587'
        self['elbeuser'] = 'root'
        self['elbepass'] = 'foo'

        if 'ELBE_SOAPPORT' in os.environ:
            self['soapport'] = os.environ['ELBE_SOAPPORT']

        if 'ELBE_SOAPHOST' in os.environ:
            self['soaphost'] = os.environ['ELBE_SOAPHOST']

        if 'ELBE_USER' in os.environ:
            self['elbeuser'] = os.environ['ELBE_USER']

        if 'ELBE_PASS' in os.environ:
            self['elbepass'] = os.environ['ELBE_PASS']


cfg = Config()


def add_argument_soaptimeout(parser):
    parser.add_argument(
        '--soaptimeout',
        type=int,
        default=os.environ.get('ELBE_SOAPTIMEOUT_SECS', '90'),
    )


def add_argument_soapport(parser_or_func, arg='--port'):
    return add_argument_to_parser_or_function(
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

    devel = parser.add_argument_group(
        'options for elbe developers',
        "Caution: Don't use these options in a productive environment")
    devel.add_argument('--debug', action='store_true',
                       dest='debug', default=False,
                       help='Enable debug mode.')


def add_argument_sshport(parser_or_func):
    return add_argument_to_parser_or_function(
        parser_or_func,
        '--sshport',
        type=int,
        default=os.environ.get('ELBE_SSHPORT', '5022'),
    )
