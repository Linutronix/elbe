# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2016-2018 Linutronix GmbH

import os


class Config(dict):
    def __init__(self):
        dict.__init__(self)
        self['soaphost'] = 'localhost'
        self['soapport'] = '7587'
        self['sshport'] = '5022'
        self['elbeuser'] = 'root'
        self['elbepass'] = 'foo'
        self['initvm_domain'] = 'initvm'

        if 'ELBE_SOAPPORT' in os.environ:
            self['soapport'] = os.environ['ELBE_SOAPPORT']

        if 'ELBE_SSHPORT' in os.environ:
            self['sshport'] = os.environ['ELBE_SSHPORT']

        if 'ELBE_SOAPHOST' in os.environ:
            self['soaphost'] = os.environ['ELBE_SOAPHOST']

        if 'ELBE_USER' in os.environ:
            self['elbeuser'] = os.environ['ELBE_USER']

        if 'ELBE_PASS' in os.environ:
            self['elbepass'] = os.environ['ELBE_PASS']

        if 'ELBE_INITVM_DOMAIN' in os.environ:
            self['initvm_domain'] = os.environ['ELBE_INITVM_DOMAIN']


cfg = Config()


def add_argument_soaptimeout(parser):
    parser.add_argument(
        '--soaptimeout',
        type=int,
        default=os.environ.get('ELBE_SOAPTIMEOUT_SECS', '90'),
    )
