# ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (c) 2014, 2016-2017 Manuel Traut <manut@linutronix.de>
# Copyright (c) 2015-2016 Torben Hohn <torben.hohn@linutronix.de>
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import print_function

import sys

from esoap import ESoap

from beaker.middleware import SessionMiddleware
from cherrypy.process.plugins import SimplePlugin

try:
    from spyne import Application
    from spyne.protocol.soap import Soap11
    from spyne.server.wsgi import WsgiApplication
except ImportError as e:
    print("failed to import spyne", file=sys.stderr)
    print("please install python(3)-spyne", file=sys.stderr)
    sys.exit(20)

from elbepack.projectmanager import ProjectManager


class EsoapApp(Application):
    def __init__(self, *args, **kargs):
        Application.__init__(self, *args, **kargs)
        self.pm = ProjectManager("/var/cache/elbe")


class MySession (SessionMiddleware, SimplePlugin):
    def __init__(self, app, pm, engine):
        self.pm = pm
        SessionMiddleware.__init__(self, app)

        SimplePlugin.__init__(self, engine)
        self.subscribe()

    def stop(self):
        self.pm.stop()

    def __call__(self, environ, start_response):
        # example to hook into wsgi environment
        if environ['PATH_INFO'].startswith('/FILE:'):
            f = environ['PATH_INFO'][6:]
            # return f

        return SessionMiddleware.__call__(self, environ, start_response)


def get_app(engine):

    app = EsoapApp([ESoap], 'soap',
                   in_protocol=Soap11(validator='lxml'),
                   out_protocol=Soap11())

    wsgi = WsgiApplication(app)
    return MySession(wsgi, app.pm, engine)
