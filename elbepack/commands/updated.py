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
import soaplib
import sys
import time
import threading

from optparse import OptionParser
from soaplib.service import soapmethod
from soaplib.wsgi_soap import SimpleWSGISoapApp
from soaplib.serializers.primitive import String, Array
from suds.client import Client
from wsgiref.simple_server import make_server
from zipfile import (ZipFile, BadZipfile)

from elbepack.aptprogress import (ElbeInstallProgress, ElbeAcquireProgress)
from elbepack.gpg import unsign_file
from elbepack.treeutils import etree
from elbepack.xmldefaults import ElbeDefaults

class UpdateStatus:
    monitor = None
    observer = None
    soapserver = None
    stop = False
    step = 0
    nosign = False

status = UpdateStatus ()

class UpdateService (SimpleWSGISoapApp):

    @soapmethod (_returns=String)
    def list_snapshots (self):
        snapshots = ""
        lists = os.listdir ("/etc/apt/sources.list.d")

        for l in lists:
            snapshots += l.split (".")[0] + ","

        return snapshots

    @soapmethod (String, _returns=String)
    def apply_snapshot (self, version):
        try:
            xml = etree ("/opt/elbe/" + version + "/new.xml")
        except:
            return "snapshot %s not found" % version
        try:
            apply_update (xml)
        except Exception, err:
            print Exception, err
            status.step = 0
            return "apply snapshot %s failed" % version

        status.step = 0
        return "snapshot %s applied" % version

    @soapmethod (String)
    def register_monitor (self, wsdl_url):
        status.monitor = Client (wsdl_url)
        log ("connection established")

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

    log ("ERROR: " + pkg.name + version + " is not available in the cache")

def apply_update (xml):

    fpl = xml.node ("fullpkgs")

    sources = apt_pkg.SourceList ()
    sources.read_main_list ()

    apt_pkg.init ()
    cache = apt_pkg.Cache ()

    status.step = 1
    log ("updating package cache ...")
    cache.update (ElbeAcquireProgress (cb=log), sources)
    # quote from python-apt api doc: "A call to this method does not affect the
    # current Cache object, instead a new one should be created in order to use
    # the changed index files."
    cache = apt_pkg.Cache ()
    depcache = apt_pkg.DepCache (cache)
    hl_cache = apt.cache.Cache ()
    hl_cache.update ()

    # go through package cache, if a package is in the fullpkg list of the XML
    #  mark the package for installation (with the specified version)
    #  if it is not mentioned in the fullpkg list purge the package out of the
    #  system.
    status.step = 2
    log ("calculating packages to install/remove ...")
    count = len (hl_cache)
    step = count / 10
    i = 0
    percent = 0
    for p in hl_cache:
        i = i + 1
        if not (i % step):
            percent = percent + 10
            log (str (percent) + "% - " + str (i) + "/" + str (count))

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

    status.step = 3
    log ("applying snapshot ...")
    depcache.commit (ElbeAcquireProgress (cb=log), ElbeInstallProgress (cb=log))

def log (msg):

    global status

    if status.step:
        msg = "(" + str (status.step) + "/3) " + msg

    if status.monitor:
        try:
            status.monitor.service.msg (msg)
        except:
            print "logging to monitor failed, removing monitor connection"
            status.monitor = None
            print msg
    else:
        print msg

def update (upd_file):

    global status

    log ( "updating.. " + upd_file)

    try:
        upd_file_z = ZipFile (upd_file)
    except BadZipfile:
        log ("update aborted (bad zip file: %s)" % upd_file)
        return

    if not "new.xml" in upd_file_z.namelist ():
        log ("update invalid (new.xml missing)")
        return

    upd_file_z.extract ("new.xml", "/tmp/")

    xml = etree ("/tmp/new.xml")
    prefix = "/opt/elbe/" + xml.text ("/project/name")
    prefix += "_" + xml.text ("/project/version") + "/"

    log ("preparing update: " + prefix)

    for i in upd_file_z.namelist ():

        (dirname, filename) = os.path.split (i)

        try:
            upd_file_z.extract (i, prefix)
        except OSError:
            log ("extraction failed: %s" % sys.exc_info () [1])
            return

    update_sourceslist (xml, prefix + "repo")
    try:
        apply_update (xml)
    except Exception, err:
        print Exception, err
        status.step = 0
        log ("apply update failed: " + prefix)
        return

    status.step = 0
    log ("update done: " + prefix)

def action_select (fname):

    global status

    action = fname.split ('.') [-1]

    if action == "upd":
        update (fname)
    else:
        log ("unhandled file: " + fname)

class FileMonitor (pyinotify.ProcessEvent):
    def process_IN_CLOSE_WRITE (self, event):

        global status

        extension = event.pathname.split ('.') [-1]

        if extension == "gpg":
            fname = unsign_file (event.pathname)
            if fname:
                action_select (fname)
            else:
                log ("checking signature failed: " + event.pathname)

        elif status.nosign:
            action_select (event.pathname)

def shutdown (signum, fname):

    global status

    status.stop = True
    status.observer = None

class ObserverThread (threading.Thread):

    def __init__ (self):
                threading.Thread.__init__ (self)

    def run (self):

        global status

        while 1:
            if status.observer.check_events (timeout=1000):
                status.observer.read_events ()
                status.observer.process_events ()

            if status.stop:
                if status.soapserver:
                    status.soapserver.shutdown ()
                return

def run_command (argv):

    global status

    oparser = OptionParser (usage="usage: %prog init [options] <filename>")

    oparser.add_option ("--directory", dest="update_dir",
                        help="monitor dir (default is /opt/elbe/updates)",
                        metavar="FILE" )

    oparser.add_option ("--host", dest="host", default="",
                        help="listen host")

    oparser.add_option ("--port", dest="port", default=8088,
                        help="listen port")

    oparser.add_option ("--nosign", action="store_true", dest="nosign",
                        default=False,
                        help="accept none signed files")

    (opt,args) = oparser.parse_args(argv)

    if opt.nosign:
        status.nosign = True

    if not opt.update_dir:
        update_dir = "/opt/elbe/updates"
    else:
        update_dir = opt.update_dir

    if not os.path.isdir (update_dir):
        os.makedirs (update_dir)

    wm = pyinotify.WatchManager ()
    status.observer = pyinotify.Notifier (wm)
    wm.add_watch (update_dir, pyinotify.IN_CLOSE_WRITE, proc_fun=FileMonitor ())
    signal.signal (signal.SIGTERM, shutdown)

    obs_thread = ObserverThread ()
    obs_thread.start ()

    status.soapserver = make_server (opt.host, int (opt.port), UpdateService ())
    try:
        status.soapserver.serve_forever ()
    except:
        shutdown (1, "now")

    obs_thread.join ()
