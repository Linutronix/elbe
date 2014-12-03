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
from syslog import syslog
from wsgiref.simple_server import make_server
from zipfile import (ZipFile, BadZipfile)

from elbepack.aptprogress import (ElbeInstallProgress, ElbeAcquireProgress)
from elbepack.gpg import unsign_file
from elbepack.treeutils import etree
from elbepack.xmldefaults import ElbeDefaults

from multiprocessing import Process, Queue

class UpdateStatus:
    monitor = None
    observer = None
    soapserver = None
    stop = False
    step = 0
    nosign = False
    verbose = False
    repo_dir = ""

status = UpdateStatus ()

class UpdateService (SimpleWSGISoapApp):

    @soapmethod (_returns=String)
    def list_snapshots (self):
        # use comma seperated string because array of string triggers a bug in
        # python suds :(
        snapshots = ""

        if os.path.isfile ("/etc/elbe_base.xml"):
            snapshots += "base_version,"

        lists = os.listdir ("/etc/apt/sources.list.d")

        for l in lists:
            snapshots += l[:len(l)-5] + ","

        return snapshots

    @soapmethod (String, _returns=String)
    def apply_snapshot (self, version):
        if version == "base_version":
            fname = "/etc/elbe_base.xml"
        else:
            fname = status.repo_dir + "/" + version + "/new.xml"

        try:
            apply_update (fname)
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

class rw_access_file:
    def __init__ (self, filename):
        self.filename = filename
        self.rw = rw_access (filename)

    def __enter__ (self):
        self.rw.__enter__ ()
        self.f = open (self.filename, 'w')
        return self.f

    def __exit__ (self, type, value, traceback):
        if os.path.isfile (self.filename):
            self.f.close ()
        self.rw.__exit__ (type, value, traceback)

class rw_access:
    def __init__ (self, directory):
        self.directory = directory
        self.mount = self.get_mount ()
        self.mount_orig = self.get_mount_status ()

    def __enter__ (self):
        if self.mount_orig == 'ro':
            log ("remount %s read/writeable" % self.mount)
            cmd = "mount -o remount,rw %s" % self.mount
            os.system (cmd)

    def __exit__ (self, type, value, traceback):
        if self.mount_orig == 'ro':
            log ("remount %s readonly" % self.mount)
            os.system ("sync")
            cmd = "mount -o remount,ro %s" % self.mount
            ret = os.system (cmd)

    def get_mount_status (self):
        with open ('/etc/mtab') as mtab:
            mtab_lines = mtab.readlines ()
            # take care, to use the last mount if overlayed mountpoints are
            # used: e.g. rootfs / rootfs rw 0 0 vs. /dev/root / ext2 ro
            ret = 'unknown'
            for ml in mtab_lines:
                mle = ml.split (' ')
                if mle[1] == self.mount:
                    attr_list = mle[3].split(',')
                    for attr in attr_list:
                        if attr == 'ro':
                            ret = 'ro'
                        elif attr == 'rw':
                            ret = 'rw'
        return ret

    def get_mount (self):
        path = os.path.realpath (os.path.abspath (self.directory))
        while path != os.path.sep:
            if os.path.ismount (path):
                return path
            path = os.path.abspath (os.path.join (path, os.pardir))
        return path

def fname_replace (s):
    allowed = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
    allowed += "0123456789"
    allowed += "_-."
    res = ""
    for c in s:
        if c in allowed:
            res += c
        else:
            res += '_'
    return res

def update_sourceslist (xml, update_dir):
    deb =  "deb file://" + update_dir + " " + xml.text ("/project/suite")
    deb += " main\n"
    fname = "/etc/apt/sources.list.d/"
    fname += fname_replace (xml.text ("/project/name")) + "_"
    fname += fname_replace (xml.text ("/project/version"))
    fname += ".list"

    with rw_access_file (fname) as f:
        f.write (deb)

def mark_install (depcache, pkg, version, auto):
    for v in pkg.version_list:
        if v.ver_str == str (version):
            depcache.set_candidate_ver (pkg, v)
            depcache.mark_install (pkg, False, not auto)
            return

    log ("ERROR: " + pkg.name + version + " is not available in the cache")

def _apply_update (fname):

    try:
        xml = etree (fname)
    except:
        return "read %s failed" % fname

    fpl = xml.node ("fullpkgs")

    sources = apt_pkg.SourceList ()
    sources.read_main_list ()

    log ("initialize apt")
    apt_pkg.init ()
    cache = apt_pkg.Cache ()

    status.step = 1
    log ("updating package cache")
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
    log ("calculating packages to install/remove")
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
    log ("applying snapshot")
    depcache.commit (ElbeAcquireProgress (cb=log), ElbeInstallProgress (cb=log))
    del depcache
    del hl_cache
    del cache
    del sources

    version_file = open("/etc/updated_version", "w")
    version_file.write( xml.text ("/project/version") )
    version_file.close()

def apply_update (fname):
    # As soon as python-apt closes its opened files on object deletion
    # we can drop this fork workaround. As long as they keep their files
    # open, we run the code in an own fork, than the files are closed on
    # process termination an we can remount the filesystem readonly
    # without errors.
    p = Process (target=_apply_update, args=(fname, ))
    with rw_access ("/"):
        p.start ()
        p.join ()

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
    try:
        syslog (msg)
    except:
        print msg
    if status.verbose:
        print msg

def update (upd_file):

    global status

    log ( "updating: " + upd_file)

    try:
        upd_file_z = ZipFile (upd_file)
    except BadZipfile:
        log ("update aborted (bad zip file: %s)" % upd_file)
        return

    if not "new.xml" in upd_file_z.namelist ():
        log ("update invalid (new.xml missing)")
        return

    with rw_access ("/tmp"):
        upd_file_z.extract ("new.xml", "/tmp/")

    xml = etree ("/tmp/new.xml")
    prefix = status.repo_dir + "/" + fname_replace (xml.text ("/project/name"))
    prefix += "_" + fname_replace (xml.text ("/project/version")) + "/"

    log ("preparing update: " + prefix)

    with rw_access (prefix):
        for i in upd_file_z.namelist ():

            (dirname, filename) = os.path.split (i)

            try:
                upd_file_z.extract (i, prefix)
            except OSError:
                log ("extraction failed: %s" % sys.exc_info () [1])
                return

    try:
        update_sourceslist (xml, prefix + "repo")
    except Exception, err:
        log (str (err))
        status.step = 0
        log ("update apt sources list failed: " + prefix)
        return

    try:
        apply_update ("/tmp/new.xml")
    except Exception, err:
        log (str (err))
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

        log ("checking file: " + str(event.pathname))
        extension = event.pathname.split ('.') [-1]

        if extension == "gpg":
            fname = unsign_file (event.pathname)
            if fname:
                action_select (fname)
            else:
                log ("checking signature failed: " + event.pathname)

        elif status.nosign:
            action_select (event.pathname)
        else:
            log ("ignore file: " + str(event.pathname))

def shutdown (signum, fname):

    global status

    status.stop = True
    status.observer = None

class ObserverThread (threading.Thread):

    def __init__ (self):
                threading.Thread.__init__ (self)

    def run (self):

        global status

        log ("monitoring updated dir")

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
