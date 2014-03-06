#!/usr/bin/env python

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

import os
import signal
import sys
import time

from watchdog.observers import Observer
from watchdog.events import FileSystemEventFileMonitor

from optparse import OptionParser

from elbepack.treeutils import etree
from elbepack.xmldefaults import ElbeDefaults

observer = None
stop = False

class FileMonitor (FileSystemEventFileMonitor):
    def on_created (self, event):
        print event

    def on_deleted(self, event):
        print event

    def on_moved(self, event):
        print event

def shutdown(signum, fname):

    global observer
    global stop

    observer.stop ()
    observer.join ()
    observer = None
    stop = True

def run_command (argv):

    global observer
    global stop

    oparser = OptionParser (usage="usage: %prog init [options] <filename>")

    oparser.add_option ("--directory", dest="update_dir",
                        help="monitor dir (default is /opt/elbe/updates)",
                        metavar="FILE" )

    (opt,args) = oparser.parse_args(argv)

    if not opt.update_dir:
        update_dir = "/opt/elbe/updates"
    else:
        update_dir = opt.update_dir

    if not os.path.isdir (update_dir):
        os.mkdir (update_dir)

    observer = Observer ()
    observer.schedule(FileMonitor (), path=update_dir, recursive=True)
    observer.start ()
    signal.signal (signal.SIGTERM, shutdown)

    while 1:
        time.sleep (1)
        print "."

        if stop:
            print "shutdown"
            sys.exit (0)
