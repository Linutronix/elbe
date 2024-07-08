# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2015 Ferdinand Schwenk <ferdinand@ping.lan>
# SPDX-FileCopyrightText: 2017 Linutronix GmbH

import argparse
import os
import signal
import sys
from wsgiref.simple_server import make_server

from spyne.protocol.soap import Soap11
from spyne.server.wsgi import WsgiApplication

from elbepack.updated import UpdateApplication, UpdateService, UpdateStatus
from elbepack.updated_monitors import FileMonitor

try:
    from elbepack.updated_monitors import USBMonitor
    usbmonitor_available = True
except ImportError:
    usbmonitor_available = False


def shutdown(_signum, _fname, status):
    status.stop = True
    for mon in status.monitors:
        mon.stop()


def run_command(argv):

    status = UpdateStatus()

    aparser = argparse.ArgumentParser(prog='elbe updated')

    aparser.add_argument('--directory', dest='update_dir',
                         help='monitor dir (default is /var/cache/elbe/updates)',
                         metavar='FILE')

    aparser.add_argument('--repocache', dest='repo_dir',
                         help='monitor dir (default is /var/cache/elbe/repos)',
                         metavar='FILE')

    aparser.add_argument('--host', dest='host', default='',
                         help='listen host')

    aparser.add_argument('--port', dest='port', default=8088,
                         help='listen port')

    aparser.add_argument('--nosign', action='store_true', dest='nosign',
                         default=False,
                         help='accept none signed files')

    aparser.add_argument('--verbose', action='store_true', dest='verbose',
                         default=False,
                         help='force output to stdout instead of syslog')

    aparser.add_argument('--usb', action='store_true', dest='use_usb',
                         default=False,
                         help='monitor USB devices')

    args = aparser.parse_args(argv)

    status.nosign = args.nosign
    status.verbose = args.verbose

    if not args.update_dir:
        update_dir = '/var/cache/elbe/updates'
    else:
        update_dir = args.update_dir

    if not args.repo_dir:
        status.repo_dir = '/var/cache/elbe/repos'
    else:
        status.repo_dir = args.repo_dir

    if not os.path.isdir(update_dir):
        os.makedirs(update_dir)

    status.monitors = []

    fm = FileMonitor(status, update_dir)
    status.monitors.append(fm)
    if args.use_usb:
        if usbmonitor_available:
            um = USBMonitor(status, recursive=False)
            status.monitors.append(um)
        else:
            status.log(
                'USB Monitor has been requested. '
                'This requires pyudev module which could not be imported.')
            sys.exit(1)

    signal.signal(signal.SIGTERM, shutdown)

    for mon in status.monitors:
        mon.start()

    application = UpdateApplication([UpdateService], 'update',
                                    in_protocol=Soap11(validator='lxml'),
                                    out_protocol=Soap11())
    application.status = status

    wsgi_application = WsgiApplication(application)

    status.soapserver = make_server(args.host, int(args.port),
                                    wsgi_application)

    try:
        status.soapserver.serve_forever()
    except BaseException:
        shutdown(1, 'now', status)

    for mon in status.monitors:
        mon.join()
