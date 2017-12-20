# ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (c) 2015 Ferdinand Schwenk <ferdinand@ping.lan>
# Copyright (c) 2017 Kurt Kanzenbach <kurt@linutronix.de>
# Copyright (c) 2017 Manuel Traut <manut@linutronix.de>
#
# SPDX-License-Identifier: GPL-3.0-or-later

import os
import signal
import sys

from optparse import OptionParser
from wsgiref.simple_server import make_server

from spyne.protocol.soap import Soap11
from spyne.server.wsgi import WsgiApplication

from elbepack.updated import UpdateStatus, UpdateService, UpdateApplication
from elbepack.updated_monitors import FileMonitor
try:
    from elbepack.updated_monitors import USBMonitor
    usbmonitor_available = True
except ImportError:
    usbmonitor_available = False


def shutdown(signum, fname, status):
    status.stop = True
    for mon in status.monitors:
        mon.stop()


def run_command(argv):

    status = UpdateStatus()

    oparser = OptionParser(usage="usage: %prog updated [options] <filename>")

    oparser.add_option("--directory", dest="update_dir",
                       help="monitor dir (default is /var/cache/elbe/updates)",
                       metavar="FILE")

    oparser.add_option("--repocache", dest="repo_dir",
                       help="monitor dir (default is /var/cache/elbe/repos)",
                       metavar="FILE")

    oparser.add_option("--host", dest="host", default="",
                       help="listen host")

    oparser.add_option("--port", dest="port", default=8088,
                       help="listen port")

    oparser.add_option("--nosign", action="store_true", dest="nosign",
                       default=False,
                       help="accept none signed files")

    oparser.add_option("--verbose", action="store_true", dest="verbose",
                       default=False,
                       help="force output to stdout instead of syslog")

    oparser.add_option("--usb", action="store_true", dest="use_usb",
                       default=False,
                       help="monitor USB devices")

    (opt, args) = oparser.parse_args(argv)

    status.nosign = opt.nosign
    status.verbose = opt.verbose

    if not opt.update_dir:
        update_dir = "/var/cache/elbe/updates"
    else:
        update_dir = opt.update_dir

    if not opt.repo_dir:
        status.repo_dir = "/var/cache/elbe/repos"
    else:
        status.repo_dir = opt.repo_dir

    if not os.path.isdir(update_dir):
        os.makedirs(update_dir)

    status.monitors = []

    fm = FileMonitor(status, update_dir)
    status.monitors.append(fm)
    if opt.use_usb:
        if usbmonitor_available:
            um = USBMonitor(status, recursive=False)
            status.monitors.append(um)
        else:
            status.log(
                "USB Monitor has been requested. "
                "This requires pyudev module which could not be imported.")
            sys.exit(1)

    signal.signal(signal.SIGTERM, shutdown)

    for mon in status.monitors:
        mon.start()

    application = UpdateApplication([UpdateService], 'update',
                                    in_protocol=Soap11(validator='lxml'),
                                    out_protocol=Soap11())
    application.status = status

    wsgi_application = WsgiApplication(application)

    status.soapserver = make_server(opt.host, int(opt.port),
                                    wsgi_application)

    try:
        status.soapserver.serve_forever()
    except BaseException:
        shutdown(1, "now", status)

    for mon in status.monitors:
        mon.join()
