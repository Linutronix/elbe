# ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (c) 2016, 2018 Torben Hohn <torben.hohn@linutronix.de>
# Copyright (c) 2017 Kurt Kanzenbach <kurt@linutronix.de>
# Copyright (c) 2017 Manuel Traut <manut@linutronix.de>
#
# SPDX-License-Identifier: GPL-3.0-or-later

import os


class Config(dict):
    def __init__(self):
        self['soaphost'] = "localhost"
        self['soapport'] = "7587"
        self['elbeuser'] = "root"
        self['elbepass'] = "foo"
        self['pbuilder_jobs'] = "auto"
        self['initvm_domain'] = "initvm"

        if 'ELBE_SOAPPORT' in os.environ:
            self['soapport'] = os.environ['ELBE_SOAPPORT']

        if 'ELBE_SOAPHOST' in os.environ:
            self['soaphost'] = os.environ['ELBE_SOAPHOST']

        if 'ELBE_USER' in os.environ:
            self['elbeuser'] = os.environ['ELBE_USER']

        if 'ELBE_PASS' in os.environ:
            self['elbepass'] = os.environ['ELBE_PASS']

        if 'ELBE_PBUILDER_JOBS' in os.environ:
            self['pbuilder_jobs'] = os.environ['ELBE_PBUILDER_JOBS']

        if 'ELBE_INITVM_DOMAIN' in os.environ:
            self['initvm_domain'] = os.environ['ELBE_INITVM_DOMAIN']


cfg = Config()
