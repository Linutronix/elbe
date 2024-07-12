# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2014, 2017 Linutronix GmbH

import argparse
import contextlib
import errno
import importlib
import os
import socket
import wsgiref.simple_server
import wsgiref.util
from pkgutil import iter_modules

import elbepack.daemons


def _not_found(start_response):
    start_response('404 Not Found', [('Content-Type', 'text/plain')])
    return [b'not found']


class _WsgiDispatcher:
    def __init__(self, mapping):
        self.mapping = mapping

    def __call__(self, environ, start_response):
        app_name = wsgiref.util.shift_path_info(environ)
        if app_name is None:
            return _not_found(start_response)

        app = self.mapping.get(app_name)
        if app is None:
            return _not_found(start_response)

        return app(environ, start_response)


class _ElbeWSGIRequestHandler(wsgiref.simple_server.WSGIRequestHandler):
    def log_request(self, *args, **kargs):
        pass  # Noop


def get_daemonlist():
    return [x for _, x, _ in iter_modules(elbepack.daemons.__path__)]


# From sd_notify(3).
def _sd_notify(message):
    socket_path = os.environ.get('NOTIFY_SOCKET')
    if not socket_path:
        return

    if socket_path[0] not in ('/', '@'):
        raise OSError(errno.EAFNOSUPPORT, 'Unsupported socket type')

    # Handle abstract socket.
    if socket_path[0] == '@':
        socket_path = '\0' + socket_path[1:]

    with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM | socket.SOCK_CLOEXEC) as sock:
        sock.connect(socket_path)
        sock.sendall(message)


def run_command(argv):
    daemons = get_daemonlist()

    if not daemons:
        print('no elbe daemons installed')

    aparser = argparse.ArgumentParser(prog='elbe daemon')
    aparser.add_argument('--host', dest='host', default='0.0.0.0',
                         help='interface to host daemon')
    aparser.add_argument('--port', dest='port', type=int, default=7587,
                         help='port to host daemon')

    args = aparser.parse_args(argv)

    with contextlib.ExitStack() as stack:
        mapping = {}

        for d in daemons:
            print(f'enable {d}')
            module = 'elbepack.daemons.' + str(d)
            cmdmod = importlib.import_module(module)
            app = cmdmod.get_app()
            if hasattr(app, 'stop'):
                stack.callback(app.stop)
            mapping[d] = app

        dispatcher = _WsgiDispatcher(mapping)

        with wsgiref.simple_server.make_server(
                args.host, args.port, dispatcher,
                handler_class=_ElbeWSGIRequestHandler,
        ) as httpd:
            _sd_notify(b'READY=1\n'
                       b'STATUS=Serving requests\n')
            httpd.serve_forever()
