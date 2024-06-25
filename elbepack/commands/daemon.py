# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2014, 2017 Linutronix GmbH

import importlib
from optparse import OptionParser
from pkgutil import iter_modules

import cherrypy

import elbepack.daemons


def get_daemonlist():
    return [x for _, x, _ in iter_modules(elbepack.daemons.__path__)]


def run_command(argv):
    daemons = get_daemonlist()

    if not daemons:
        print('no elbe daemons installed')

    oparser = OptionParser(usage='usage: %prog')
    oparser.add_option('--host', dest='host', default='0.0.0.0',
                       help='interface to host daemon')
    oparser.add_option('--port', dest='port', type=int, default=7587,
                       help='port to host daemon')

    for d in daemons:
        # unused, compatibility with old initscripts
        oparser.add_option('--' + str(d), dest='_ignored', default=False,
                           action='store_true', help='enable ' + str(d))

    (opt, _) = oparser.parse_args(argv)

    for d in daemons:
        print(f'enable {d}')
        module = 'elbepack.daemons.' + str(d)
        cmdmod = importlib.import_module(module)
        cherrypy.tree.graft(
            cmdmod.get_app(cherrypy.engine), '/' + str(d))

    cherrypy.server.unsubscribe()
    server = cherrypy._cpserver.Server()
    server.socket_host = opt.host
    server.socket_port = opt.port
    server.thread_pool = 30

    # For SSL Support
    # server.ssl_module            = 'pyopenssl'
    # server.ssl_certificate       = 'ssl/certificate.crt'
    # server.ssl_private_key       = 'ssl/private.key'
    # server.ssl_certificate_chain = 'ssl/bundle.crt'

    server.subscribe()
    cherrypy.engine.start()
    cherrypy.engine.block()
