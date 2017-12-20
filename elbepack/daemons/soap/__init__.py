# ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (C) 2014  Linutronix GmbH
#
# This file is part of ELBE.
#
# ELBE is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# ELBE is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with ELBE.  If not, see <http://www.gnu.org/licenses/>.

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
