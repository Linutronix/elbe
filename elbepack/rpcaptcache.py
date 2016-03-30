# ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (C) 2013  Linutronix GmbH
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

from multiprocessing.util import Finalize
from apt_pkg import config, version_compare
from apt import Cache
from multiprocessing.managers import BaseManager
from elbepack.aptprogress import ElbeAcquireProgress, ElbeInstallProgress
from elbepack.asciidoclog import ASCIIDocLog
from elbepack.aptpkgutils import getalldeps, APTPackage

import os
import time
import warnings

class InChRootObject(object):
    def __init__(self, rfs):
        self.rfs = rfs
        self.rfs.enter_chroot()
        self.finalizer = Finalize(self,self.rfs.leave_chroot,exitpriority=10)

class RPCAPTCache(InChRootObject):
    def __init__( self, rfs, logpath, arch, notifier=None, norecommend = False, noauth = True ):
        self.log = ASCIIDocLog(logpath)
        self.notifier = notifier
        InChRootObject.__init__(self, rfs)
        config.set ("APT::Architecture", arch)
        if norecommend:
            config.set ("APT::Install-Recommends", "1")
        else:
            config.set ("APT::Install-Recommends", "0")

        if noauth:
            config.set ("APT::Get::AllowUnauthenticated", "1")
        else:
            config.set ("APT::Get::AllowUnauthenticated", "0")

        self.cache = Cache()
        self.cache.open()

    def dbg_dump( self, filename ):
        ts = time.localtime ()
        filename = filename + (
                '_%02d%02d%02d' % (ts.tm_hour, ts.tm_min, ts.tm_sec))
        with open (filename, 'w') as dbg:
            for p in self.cache:
                dbg.write ('%s %s %d %d %d %d %d %d %d %d %d %d %d %d\n' % (
                    p.name, p.candidate.version, p.marked_keep, p.marked_delete,
                    p.marked_upgrade, p.marked_downgrade, p.marked_install,
                    p.marked_reinstall, p.is_auto_installed, p.is_installed,
                    p.is_auto_removable, p.is_now_broken, p.is_inst_broken,
                    p.is_upgradable))

    def get_sections( self ):
        ret = list(set( [p.section for p in self.cache] ))
        ret.sort()
        return ret

    def get_pkglist( self, section ):
        if section == 'all':
            ret = [ APTPackage(p) for p in self.cache ]
        else:
            ret = [ APTPackage(p) for p in self.cache if p.section == section ]

        return ret

    def mark_install( self, pkgname, version, from_user=True, nodeps=False ):
        p = self.cache[pkgname]
        if version:
            p.candidate = p.versions[ version ]
        p.mark_install( auto_fix = not nodeps,
                auto_inst = not nodeps,
                from_user = from_user )

    def mark_install_devpkgs( self, ignore_pkgs ):
        ignore_pkgs.remove ('libc6') # we don't want to ignore libc
        # we don't want to ignore libstdc++
        try:
            ignore_pkgs.remove ('libstdc++5')
        except:
            pass
        try:
            ignore_pkgs.remove ('libstdc++6')
        except:
            pass
        # list all debian src packages of all installed packages that don't
        # come from debootstrap
        src_list = [p.candidate.source_name for p in self.cache if p.is_installed and p.name not in ignore_pkgs ]
        # go through all packages, remember package if its source package
        # matches one of the installed packages and the binary package is a
        # '-dev' package
        dev_list = [s for s in self.cache if (s.candidate.source_name in src_list and s.name.endswith ('-dev'))]
        for p in dev_list:
            p.mark_install ()
        # ensure that the symlinks package will be installed (it's needed for
        # fixing links inside the sysroot
        self.cache ['symlinks'].mark_install ()

    def cleanup (self, exclude_pkgs):
        for p in self.cache:
            if (p.is_installed and not p.is_auto_installed) or p.is_auto_removable:
                remove = True
                for x in exclude_pkgs:
                    if x == p.name:
                        remove = False
                if remove:
                    p.mark_delete( auto_fix=True, purge=True )

    def mark_upgrade( self, pkgname, version ):
        p = self.cache[pkgname]
        if version:
            p.candidate = p.versions[ version ]
        p.mark_upgrade()

    def mark_delete( self, pkgname, version ):
        p = self.cache[pkgname]
        p.mark_delete( purge=True )

    def mark_keep( self, pkgname, version ):
        p = self.cache[pkgname]
        p.mark_keep()


    def update( self ):
        self.cache.update()
        self.cache.open()

    def co_cb(self, msg):
        if self.notifier:
            self.notifier.status (msg)

    def commit(self):
        os.environ["DEBIAN_FRONTEND"]="noninteractive"
        os.environ["DEBONF_NONINTERACTIVE_SEEN"]="true"
        self.cache.commit( ElbeAcquireProgress(cb=self.co_cb),
                           ElbeInstallProgress(cb=self.co_cb) )
        self.cache.open()

    def clear(self):
        self.cache.clear()

    def get_dependencies(self, pkgname):
        deps = getalldeps( self.cache, pkgname )
        return [APTPackage(p, cache=self.cache) for p in deps]

    def get_installed_pkgs( self, section='all' ):
        # avoid DeprecationWarning: MD5Hash is deprecated, use Hashes instead
        # triggerd by python-apt
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore",category=DeprecationWarning)
            if section == 'all':
                pl = [APTPackage(p) for p in self.cache if p.is_installed]
            else:
                pl = [APTPackage(p) for p in self.cache if (p.section == section
                    and p.is_installed)]
            return pl

    def get_fileindex( self ):
        index = {}

        for p in self.cache:
            if p.is_installed:
                for f in p.installed_files:
                    index[f] = p.name

        return index

    def get_marked_install( self, section='all' ):
        if section == 'all':
            ret = [APTPackage(p) for p in self.cache if p.marked_install]
        else:
            ret = [APTPackage(p) for p in self.cache if (p.section == section
                and p.marked_install)]
        return ret

    def get_upgradeable(self, section='all'):
        if section == 'all':
            ret = [ APTPackage(p) for p in self.cache if p.is_upgradable]
        else:
            ret = [ APTPackage(p) for p in self.cache if (p.section == section
                and p.is_upgradable)]
        return ret

    def upgrade( self, dist_upgrade = False ):
        self.cache.upgrade( dist_upgrade )

    def get_changes( self ):
        changes = self.cache.get_changes()
        return [ APTPackage(p) for p in changes ]

    def has_pkg( self, pkgname ):
        return pkgname in self.cache

    def is_installed( self, pkgname ):
        if not pkgname in self.cache:
            return False
        return self.cache[pkgname].is_installed

    def get_pkg( self, pkgname ):
        return APTPackage( self.cache[pkgname] )

    def get_pkgs( self, pkgname ):
        return [APTPackage (self.cache[p]) for p in sorted (self.cache.keys()) if pkgname in p.lower()]

    def compare_versions( self, ver1, ver2 ):
        return version_compare( ver1, ver2 )

    def download_binary( self, pkgname, path, version=None ):
        p = self.cache[pkgname]
        if version is None:
            pkgver = p.installed
        else:
            pkgver = p.versions[version]

        rel_filename = pkgver.fetch_binary(path,
                ElbeAcquireProgress(cb=self.co_cb))
        return self.rfs.fname( rel_filename )

    def download_source( self, pkgname, path, version=None ):
        p = self.cache[pkgname]
        if version is None:
            pkgver = p.installed
        else:
            pkgver = p.versions[version]

        rel_filename = pkgver.fetch_source(path,
                ElbeAcquireProgress(cb=self.co_cb), unpack=False)
        return self.rfs.fname( rel_filename )


class MyMan(BaseManager):
    pass

MyMan.register( "RPCAPTCache", RPCAPTCache )

def get_rpcaptcache(rfs, logpath, arch, notifier=None):
    mm = MyMan()
    mm.start()

    return mm.RPCAPTCache(rfs, logpath, arch, notifier)
