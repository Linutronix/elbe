#!/usr/bin/env python

# ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (C) 2015 emtrion GmbH
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
import errno
import os
import subprocess
import sys
import threading

from multiprocessing import Process
from shutil import copyfile, rmtree, copy
from spyne import Application
from spyne.service import ServiceBase
from spyne.decorator import rpc
from spyne.model.primitive import String
from suds.client import Client
from syslog import syslog
from zipfile import (ZipFile, BadZipfile)

from elbepack.aptprogress import (ElbeInstallProgress,
 ElbeAcquireProgress, ElbeOpProgress)
from elbepack.gpg import unsign_file
from elbepack.treeutils import etree

downgrade_prevention_feature_available = True
try:
    from packaging import version
except ImportError:
    downgrade_prevention_feature_available = False

class UpdateStatus:
    def __init__ (self):
        self.monitor = None
        self.observer = None
        self.soapserver = None
        self.stop = False
        self.step = 0
        self.nosign = False
        self.verbose = False
        self.repo_dir = ""
        self.status_file = '/var/cache/elbe/update_state.txt'
        with rw_access_file (self.status_file, self) as f:
            f.write ('ready')
            f.truncate ()

    def write_status (self, msg):
        with rw_access_file (self.status_file, self) as f:
            f.seek (0)
            f.write (msg)
            f.truncate ()

    def set_progress (self, step, percent=''):
        self.step = step
        self.write_status ('in_progress\t%d\t%s' % (step, percent))

    def set_finished (self, result):
        self.step = 0
        self.write_status ('finished\t%s' % result)

    def log (self, msg):
        if not msg.endswith ('\n'):
            msg += '\n'

        # parse progress of apt from aptprogress output
        if self.step == 3:
            msg_a = msg.split()
            self.set_progress (3, msg_a [0])

        if self.step:
            msg = "(" + str (self.step) + "/3) " + msg
        if self.monitor:
            try:
                self.monitor.service.msg (msg)
            except:
                print "logging to monitor failed, removing monitor connection"
                self.monitor = None
                print msg
        try:
            syslog (msg)
        except:
            print msg
        if self.verbose:
            print msg

class UpdateApplication (Application):
    def __init__(self, *args, **kargs):
        Application.__init__(self, *args, **kargs)
        self.status = UpdateStatus ()

class UpdateService (ServiceBase):
    @rpc (_returns=String)
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

    @rpc (String, _returns=String)
    def apply_snapshot (self, version):
        if version == "base_version":
            fname = "/etc/elbe_base.xml"
        else:
            fname = self.app.status.repo_dir + "/" + version + "/new.xml"

        try:
            apply_update (fname, self.app.status)
        except Exception, err:
            print Exception, err
            self.app.status.set_finished ('error')
            return "apply snapshot %s failed" % version

        self.app.status.set_finished ('OK')
        return "snapshot %s applied" % version

    @rpc (String)
    def register_monitor (self, wsdl_url):
        self.app.status.monitor = Client (wsdl_url)
        self.app.status.log ("connection established")

class rw_access_file:
    def __init__ (self, filename, status):
        self.filename = filename
        self.rw = rw_access (filename, status)

    def __enter__ (self):
        self.rw.__enter__ ()
        self.f = open (self.filename, 'w')
        return self.f

    def __exit__ (self, type, value, traceback):
        if os.path.isfile (self.filename):
            self.f.close ()
        self.rw.__exit__ (type, value, traceback)

class rw_access:
    def __init__ (self, directory, status):
        self.status = status
        self.directory = directory
        self.mount = self.get_mount ()
        self.mount_orig = self.get_mount_status ()

    def __enter__ (self):
        if self.mount_orig == 'ro':
            self.status.log ("remount %s read/writeable" % self.mount)
            cmd = "mount -o remount,rw %s" % self.mount
            os.system (cmd)

    def __exit__ (self, type, value, traceback):
        if self.mount_orig == 'ro':
            self.status.log ("remount %s readonly" % self.mount)
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

def update_sourceslist (xml, update_dir, status):
    # only create sources list entry if repo is valid
    if not os.path.isdir (update_dir + '/dists'):
        status.log ('invalid repository, not added to sources.list')
        return

    deb =  "deb file://" + update_dir + " " + xml.text ("/project/suite")
    deb += " main\n"
    fname = "/etc/apt/sources.list.d/"
    fname += fname_replace (xml.text ("/project/name")) + "_"
    fname += fname_replace (xml.text ("/project/version"))
    fname += ".list"

    with rw_access_file (fname, status) as f:
        f.write (deb)

def mark_install (depcache, pkg, version, auto, status):
    for v in pkg.version_list:
        if v.ver_str == str (version):
            depcache.set_candidate_ver (pkg, v)
            depcache.mark_install (pkg, False, not auto)
            return

    status.log ("ERROR: " + pkg.name + version + " is not available in the cache")

def _apply_update (fname, status):

    try:
        xml = etree (fname)
    except:
        raise Exception ( "reading %s failed " % fname )

    fpl = xml.node ("fullpkgs")

    sources = apt_pkg.SourceList ()
    sources.read_main_list ()

    status.log ("initialize apt")
    apt_pkg.init ()
    cache = apt_pkg.Cache (progress=ElbeOpProgress (cb=status.log))

    status.set_progress (1)
    status.log ("updating package cache")
    cache.update (ElbeAcquireProgress (cb=status.log), sources)
    # quote from python-apt api doc: "A call to this method does not affect the
    # current Cache object, instead a new one should be created in order to use
    # the changed index files."
    cache = apt_pkg.Cache (progress=ElbeOpProgress (cb=status.log))
    depcache = apt_pkg.DepCache (cache)
    hl_cache = apt.cache.Cache (progress=ElbeOpProgress (cb=status.log))
    hl_cache.update (fetch_progress=ElbeAcquireProgress (cb=status.log))

    # go through package cache, if a package is in the fullpkg list of the XML
    #  mark the package for installation (with the specified version)
    #  if it is not mentioned in the fullpkg list purge the package out of the
    #  system.
    status.set_progress (2)
    status.log ("calculating packages to install/remove")
    count = len (hl_cache)
    step = count / 10
    i = 0
    percent = 0
    for p in hl_cache:
        i = i + 1
        if not (i % step):
            percent = percent + 10
            status.log (str (percent) + "% - " + str (i) + "/" + str (count))
            status.set_progress (2, str (percent) + "%")

        pkg = cache [p.name]
        marked = False
        for fpi in fpl:
            if pkg.name == fpi.et.text:
                mark_install (depcache, pkg,
                            fpi.et.get('version'),
                            fpi.et.get('auto'),
                            status)
                marked = True

        if not marked:
            depcache.mark_delete (pkg, True)

    status.set_progress (3)
    status.log ("applying snapshot")
    depcache.commit (ElbeAcquireProgress (cb=status.log),
                     ElbeInstallProgress (cb=status.log))
    del depcache
    del hl_cache
    del cache
    del sources

    version_file = open("/etc/updated_version", "w")
    version_file.write( xml.text ("/project/version") )
    version_file.close()


def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as exc:
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else: raise

def execute (cmd, status):
    output = subprocess.check_output (cmd, stderr=subprocess.STDOUT)
    for o in output.rstrip ().split ('\n'):
        if o:
            status.log (o)

def pre_sh (current_version, target_version, status):
    if os.path.isfile('/var/cache/elbe/' + 'pre.sh'):
        execute (
          ['/var/cache/elbe/' + 'pre.sh', current_version, target_version],
          status)

def post_sh (current_version, target_version, status):
    if os.path.isfile('/var/cache/elbe/' + 'post.sh'):
        execute (
          ['/var/cache/elbe/' + 'post.sh', current_version, target_version],
          status)

def get_target_version (fname):
    xml = etree (fname)
    return xml.text ("/project/version")

def get_current_version ():
    with open ("/etc/updated_version", "r") as version_file:
        return version_file.read ()

def get_base_version ():
    xml = etree ("/etc/elbe_base.xml")
    return xml.text ("/project/version")

def is_downgrade (target_version, current_version, base_version):
    current = current_version
    if current == "":
        current = base_version
    return version.parse (target_version) < version.parse (current)

def is_downgrade_allowed ():
    return os.path.isfile ("/var/cache/elbe/.downgrade_allowed")

def reject_downgrade (status, new_xml_file):
    t_ver = get_target_version(new_xml_file)
    b_ver = get_base_version()

    try:
        c_ver = get_current_version()
    except IOError as e:
        status.log ('get current version failed: ' + str (e))
        c_ver = ""

    if is_downgrade (t_ver, c_ver, b_ver) and not is_downgrade_allowed ():
        status.log ('Update is a downgrade and downgrades are not allowed')
        return True

    return False

def apply_update (fname, status):
    # As soon as python-apt closes its opened files on object deletion
    # we can drop this fork workaround. As long as they keep their files
    # open, we run the code in an own fork, than the files are closed on
    # process termination an we can remount the filesystem readonly
    # without errors.
    p = Process (target=_apply_update, args=(fname, status))
    with rw_access ("/", status):
        try:
            t_ver = get_target_version(fname)
        except:
            status.log ('Reading xml-file failed!')
            return

        try:
            c_ver = get_current_version()
        except IOError as e:
            status.log ('get current version failed: ' + str (e))
            c_ver = ""

        pre_sh (c_ver, t_ver, status)
        p.start ()
        p.join ()
        status.log ("cleanup /var/cache/apt/archives")
        # don't use execute() here, it results in an error that the apt-cache
        # is locked. We currently don't understand this behaviour :(
        os.system ("apt-get clean")
        if p.exitcode != 0:
            raise Exception ( "Applying update failed. See logfile for more information" )
        post_sh (c_ver, t_ver, status)

def action_select (upd_file, status):

    status.log ( "updating: " + upd_file)

    try:
        upd_file_z = ZipFile (upd_file)
    except BadZipfile:
        status.log ("update aborted (bad zip file: %s)" % upd_file)
        return

    if not "new.xml" in upd_file_z.namelist ():
        status.log ("update invalid (new.xml missing)")
        return

    with rw_access ("/tmp", status):
        upd_file_z.extract ("new.xml", "/tmp/")

    # prevent downgrades (if available)
    if downgrade_prevention_feature_available:
        try:
            if reject_downgrade (status, "/tmp/new.xml"):
                return
        except Exception as e:
            status.log ('Error while reading XML files occurred: ' + str(e))
            return

    xml = etree ("/tmp/new.xml")
    prefix = status.repo_dir + "/" + fname_replace (xml.text ("/project/name"))
    prefix += "_" + fname_replace (xml.text ("/project/version")) + "/"

    status.log ("preparing update: " + prefix)

    with rw_access (prefix, status):
        for i in upd_file_z.namelist ():

            (dirname, filename) = os.path.split (i)

            try:
                zi = upd_file_z.getinfo (i)
                upd_file_z.extract (zi, prefix)
                os.chmod (prefix + '/' + i, zi.external_attr >> 16)
            except OSError:
                status.log ("extraction failed: %s" % sys.exc_info () [1])
                return

    with rw_access ("/var/cache/elbe", status):
        if os.path.isfile(prefix + '/' + 'pre.sh'):
            try:
                copy (prefix + '/' + 'pre.sh', '/var/cache/elbe/' + 'pre.sh')
            except OSError as e:
                status.log ('presh-copy failed: ' + str (e))
            except IOError as e:
                status.log ('presh-copy failed: ' + str (e))

        if os.path.isfile(prefix + '/' + 'post.sh'):
            try:
                copy (prefix + '/' + 'post.sh', '/var/cache/elbe/' + 'post.sh')
            except OSError as e:
                status.log ('postsh-copy failed: ' + str (e))
            except IOError as e:
                status.log ('postsh-copy failed: ' + str (e))

    if os.path.isdir (prefix + "conf"):
        status.log ("copying config files:")
        for path, pathname, filenames in os.walk (prefix + "conf"):
            dst = path[len(prefix + "conf"):]
            with rw_access (dst, status):
                for f in filenames:
                    src = os.path.join (path, f)
                    status.log ("cp " + src + " " + dst)
                    try:
                        mkdir_p (dst)
                        copyfile (src, dst + '/' + f)
                    except OSError as e:
                        status.log ('failed: ' + str (e))
                    except IOError as e:
                        status.log ('failed: ' + str (e))
        with rw_access (prefix + "conf", status):
            rmtree (prefix + "conf")

    if os.path.isdir (prefix + "cmd"):
        status.log ("executing scripts:")
        for path, pathname, filenames in os.walk (prefix + "cmd"):
            for f in filenames:
                cmd = os.path.join (path, f)
                if os.path.isfile (cmd):
                    status.log ('exec: ' + cmd)
                    try:
                        execute (cmd, status)
                    except OSError as e:
                        status.log ('exec: ' + cmd + ' - ' + str (e))
        with rw_access (prefix + "cmd", status):
            rmtree (prefix + "cmd")

    if os.path.isdir (prefix + "repo"):
        try:
            update_sourceslist (xml, prefix + "repo", status)
        except Exception, err:
            status.log (str (err))
            status.set_finished ('error')
            status.log ("update apt sources list failed: " + prefix)
            return

        try:
            apply_update ("/tmp/new.xml", status)
        except Exception, err:
            status.log (str (err))
            status.set_finished ('error')
            status.log ("apply update failed: " + prefix)
            return

        status.set_finished ('OK')
        status.log ("update done: " + prefix)


def is_update_file(upd_file):
    root, extension = os.path.splitext(upd_file)
    if extension == ".gpg":
        return True

    try:
        upd_file_z = ZipFile (upd_file)
    except BadZipfile:
        return False

    if not "new.xml" in upd_file_z.namelist ():
        return False

    return True


update_lock = threading.Lock()

def handle_update_file(upd_file, status, remove=False):
    with update_lock:
        status.log ("checking file: " + str(upd_file))
        root, extension = os.path.splitext(upd_file)

        if extension == ".gpg":
            fname = unsign_file (upd_file)
            if remove:
                os.remove (upd_file)
            if fname:
                action_select (fname, status)
                if remove:
                    os.remove (fname)
            else:
                status.log ("checking signature failed: " + str(upd_file))

        elif status.nosign:
            action_select (upd_file, status)
            if remove:
                os.remove (upd_file)
        else:
            status.log ("ignore file: " + str(upd_file))


def shutdown (signum, fname, status):
    status.stop = True
    for mon in status.monitors:
        mon.stop()
