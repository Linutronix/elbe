#!/usr/bin/env python

# ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (C) 2014  Linutronix GmbH
# Copyright (C) 2015  emtrion GmbH
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

import os
import signal
import sys

from optparse import OptionParser
from wsgiref.simple_server import make_server

from elbepack.updated import UpdateStatus, UpdateService
from elbepack.updated_monitors import FileMonitor
try:
    from elbepack.updated_monitors import USBMonitor
    usbmonitor_available = True
except ImportError:
    usbmonitor_available = False


def shutdown (signum, fname, status):
    status.stop = True
    for mon in status.monitors:
        mon.stop()


def run_command (argv):

    status = UpdateStatus ()

    oparser = OptionParser (usage="usage: %prog updated [options] <filename>")

    oparser.add_option ("--directory", dest="update_dir",
                        help="monitor dir (default is /var/cache/elbe/updates)",
                        metavar="FILE" )

    oparser.add_option ("--repocache", dest="repo_dir",
                        help="monitor dir (default is /var/cache/elbe/repos)",
                        metavar="FILE" )

    oparser.add_option ("--host", dest="host", default="",
                        help="listen host")

    oparser.add_option ("--port", dest="port", default=8088,
                        help="listen port")

    oparser.add_option ("--nosign", action="store_true", dest="nosign",
                        default=False,
                        help="accept none signed files")

    oparser.add_option ("--verbose", action="store_true", dest="verbose",
                        default=False,
                        help="force output to stdout instead of syslog")

    oparser.add_option ("--usb", action="store_true", dest="use_usb",
                        default=False,
                        help="monitor USB devices")

    (opt,args) = oparser.parse_args(argv)

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

    if not os.path.isdir (update_dir):
        os.makedirs (update_dir)

    status.monitors = []

    fm = FileMonitor(status, update_dir)
    status.monitors.append(fm)
    if opt.use_usb:
        if usbmonitor_available:
            um = USBMonitor(status, recursive=False)
            status.monitors.append(um)
        else:
            status.log("USB Monitor has been requested. "
                       "This requires pyudev module which could not be imported.")
            sys.exit(1)

    signal.signal (signal.SIGTERM, shutdown)

    for mon in status.monitors:
        mon.start()

    status.soapserver = make_server (opt.host, int (opt.port),
                                     UpdateService (status))
    try:
        status.soapserver.serve_forever ()
    except:
        shutdown (1, "now", status)

    for mon in status.monitors:
        mon.join()
