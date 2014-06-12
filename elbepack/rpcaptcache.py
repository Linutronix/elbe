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

    def cleanup (self, debootstrap_pkgs):
        for p in self.cache:
            if p.is_installed:
                remove = True
                for x in debootstrap_pkgs:
                    if x == p.name:
                        remove = False
                if remove:
                    p.mark_delete( auto_fix=False, purge=True )

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
        if section == 'all':
            return [APTPackage(p) for p in self.cache if p.is_installed]
        else:
            return [APTPackage(p) for p in self.cache if (p.section == section
                and p.is_installed)]

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
