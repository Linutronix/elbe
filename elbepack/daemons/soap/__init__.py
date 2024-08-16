# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2014-2017 Linutronix GmbH

import logging
import warnings

from beaker.middleware import SessionMiddleware

# spyne uses a bundled version of six, which triggers warnings in spyne version 2.14.0.
# As the warnings can happen during any import, a scoped .catch_warnings() is not enough.
if True:  # avoid flake8 errors for the following imports
    warnings.filterwarnings('ignore', '_SixMetaPathImporter', ImportWarning)

from spyne import Application
with warnings.catch_warnings():
    warnings.filterwarnings('ignore', "'cgi' is deprecated", DeprecationWarning)
    from spyne.protocol.soap import Soap11
from spyne.server.wsgi import WsgiApplication

from elbepack.projectmanager import ProjectManager

from .esoap import ESoap

logging.getLogger('spyne').setLevel(logging.INFO)


class EsoapApp(Application):
    def __init__(self, *args, **kargs):
        super().__init__(*args, **kargs)
        self.pm = ProjectManager('/var/cache/elbe')


class MySession(SessionMiddleware):
    def __init__(self, app, pm):
        self.pm = pm
        super().__init__(app)

    def stop(self):
        self.pm.stop()


def get_app():

    app = EsoapApp([ESoap], 'soap',
                   in_protocol=Soap11(validator='lxml'),
                   out_protocol=Soap11())

    wsgi = WsgiApplication(app)
    return MySession(wsgi, app.pm)
