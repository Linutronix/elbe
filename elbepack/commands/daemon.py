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

import cherrypy

from optparse import OptionParser
from pkgutil import iter_modules

import elbepack.daemons

import sys
import os

def get_daemonlist():
    return [ x for _, x, _ in iter_modules(elbepack.daemons.__path__) ]

def run_command( argv ):
    daemons = get_daemonlist()

    if not daemons:
        print 'no elbe daemons installed'

    oparser = OptionParser(usage="usage: %prog")
    oparser.add_option( "--host", dest="host", default='0.0.0.0',
                        help="interface to host daemon" )
    oparser.add_option( "--port", dest="port", default=7587,
                        help="port to host daemon" )

    for d in daemons:
        oparser.add_option( "--"+str(d), dest=str(d), default=False,
                action="store_true", help="enable "+str(d))

    (opt,args) = oparser.parse_args(argv)

    active = False

    for d in daemons:
        for o in dir(opt):
            if str(o) == str(d):
                if getattr(opt,o) == True:
                    active = True
                    print "enable", str(d)
                    module = "elbepack.daemons." + str(d)
                    mod = __import__(module)
                    cmdmod = sys.modules[module]
                    cherrypy.tree.graft(cmdmod.get_app(cherrypy.engine), "/"+str(d))
    if not active:
        print 'no daemon activated, use'
        for d in daemons:
            print '   --'+d
        print 'to activate at least one daemon'
        return

    cherrypy.server.unsubscribe()
    server = cherrypy._cpserver.Server()
    server.socket_host = opt.host
    server.socket_port = int(opt.port)
    server.thread_pool = 30

    # For SSL Support
    # server.ssl_module            = 'pyopenssl'
    # server.ssl_certificate       = 'ssl/certificate.crt'
    # server.ssl_private_key       = 'ssl/private.key'
    # server.ssl_certificate_chain = 'ssl/bundle.crt'

    server.subscribe()
    cherrypy.engine.start()
    cherrypy.engine.block()
