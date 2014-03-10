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

import apt
import apt_pkg
import os
import pyinotify
import signal
import sys
import time
import threading

from optparse import OptionParser
from zipfile import (ZipFile, BadZipfile)

from elbepack.aptprogress import (ElbeInstallProgress, ElbeAcquireProgress)
from elbepack.treeutils import etree
from elbepack.xmldefaults import ElbeDefaults

class UpdateStatus:
    msg = "waiting"
    observer = None
    stop = False

status = UpdateStatus ()

def update_sourceslist (xml, update_dir):
    deb =  "deb file://" + update_dir + " " + xml.text ("/project/suite")
    deb += " main\n"
    fname = "/etc/apt/sources.list.d/"
    fname += xml.text ("/project/name") + "_" + xml.text ("/project/version")
    fname += ".list"

    with open (fname, 'w') as f:
        f.write (deb)

def mark_install (depcache, pkg, version, auto):
    for v in pkg.version_list:
        if v.ver_str == str (version):
            depcache.set_candidate_ver (pkg, v)
            depcache.mark_install (pkg, False, not auto)
            return

    print pkg.name, version, "is not available in the cache"

def apply_update (xml):

    fpl = xml.node ("fullpkgs")

    sources = apt_pkg.SourceList ()
    sources.read_main_list ()

    hl_cache = apt.cache.Cache ()
    cache = apt_pkg.Cache ()
    cache.update (ElbeAcquireProgress (), sources)
    depcache = apt_pkg.DepCache (cache)

    # go through package cache, if a package is in the fullpkg list of the XML
    #  mark the package for installation (with the specified version)
    #  if it is not mentioned in the fullpkg list purge the package out of the
    #  system.
    for p in hl_cache:
        pkg = cache [p.name]
        marked = False
        for fpi in fpl:
            if pkg.name == fpi.et.text:
                mark_install (depcache, pkg,
                              fpi.et.get('version'),
                              fpi.et.get('auto'))
                marked = True

        if not marked:
            depcache.mark_delete (pkg, True)

    depcache.commit (ElbeAcquireProgress (), ElbeInstallProgress ())

def update (upd_file):

    global status

    status.msg = "updating.. %s" % upd_file

    try:
        upd_file_z = ZipFile (upd_file)
    except BadZipfile:
        status.msg = "update aborted (bad zip file: %s)" % upd_file
        return

    if not "new.xml" in upd_file_z.namelist ():
        status.msg = "update invalid (new.xml missing)"
        return

    upd_file_z.extract ("new.xml", "/tmp/")

    xml = etree ("/tmp/new.xml")
    prefix = "/opt/elbe/" + xml.text ("/project/name")
    prefix += "_" + xml.text ("/project/version") + "/"

    status.msg = "updating: " + prefix

    for i in upd_file_z.namelist ():

        (dirname, filename) = os.path.split (i)
        status.msg = "unzip %s: %s" % (prefix+dirname, filename)

        try:
            if not os.path.exists (prefix+dirname):
                os.makedirs (prefix+dirname)

            upd_file_z.extract (i, prefix+dirname)
        except OSError:
            status.msg = "extraction failed: %s" % sys.exc_info () [1]
            return

    update_sourceslist (xml, prefix+"/repo")
    apply_update (xml)

    status.msg = "update done: " + prefix

def action_select (event):
    action = event.pathname.split ('.') [-1]

    if action == "upd":
        update (event.pathname)
    else:
        print "action_select: unhandled file: %s" % event.pathname

class FileMonitor (pyinotify.ProcessEvent):
    def process_IN_CLOSE_WRITE (self, event):
        action_select (event)

def shutdown (signum, fname):

    global status

    status.observer.stop ()
    status.observer = None
    status.stop = True

class ObserverThread (threading.Thread):

    def __init__(self):
                threading.Thread.__init__(self)

    def run (self):

        global status

        while 1:
            if status.observer.check_events (timeout=1000):
                status.observer.read_events ()
                status.observer.process_events ()

            if status.stop:
                print "terminate thread"
                return

def run_command (argv):

    global status

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

    wm = pyinotify.WatchManager ()
    status.observer = pyinotify.Notifier (wm)
    wm.add_watch (update_dir, pyinotify.IN_CLOSE_WRITE, proc_fun=FileMonitor ())
    signal.signal (signal.SIGTERM, shutdown)

    obs = ObserverThread ()
    obs.start ()

    # TODO status report should be done by SOAP in the future.
    #      this is just a quick hack to use multithreading from the begining
    while 1:
        try:
            time.sleep (1)
        except KeyboardInterrupt:
            status.stop = True

        print status.msg

        if status.stop:
            print "shutdown"
            sys.exit (0)

    obs.join ()
