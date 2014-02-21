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
from apt import Cache
from multiprocessing.managers import BaseManager
from elbepack.aptprogress import ElbeAcquireProgress, ElbeInstallProgress
from elbepack.asciidoclog import ASCIIDocLog

class InChRootObject(object):
    def __init__(self, rfs):
        self.rfs = rfs
        self.rfs.enter_chroot()
        self.finalizer = Finalize(self,self.rfs.leave_chroot,exitpriority=10)

class RPCAPTCache(InChRootObject):
    def __init__( self, rfs, logpath ):
        self.log = ASCIIDocLog(logpath)
        InChRootObject.__init__(self, rfs)
        self.cache = Cache()
        self.cache.open()

    def get_sections( self ):
        ret = list(set( [p.section for p in self.cache] ))
        ret.sort()
        return ret

    def get_pkglist( self, section ):
        ret = [ (p.id, p.name, 
                 p.installed and p.installed.version, 
                 p.candidate and p.candidate.version, 
                 p._pkg.selected_state                ) for p in self.cache if p.section == section ]

        return ret

    def mark_install( self, pkgname, version ):
        p = self.cache[pkgname]
        p.mark_install()

    def mark_upgrade( self, pkgname, version ):
        p = self.cache[pkgname]
        p.mark_upgrade()

    def mark_delete( self, pkgname, version ):
        p = self.cache[pkgname]
        p.mark_delete()

    def update(self):
        self.cache.update()
        self.cache.open()

    def commit(self):
        self.cache.commit( ElbeAcquireProgress(), ElbeInstallProgress() )
        self.cache.open()


class MyMan(BaseManager):
    pass

MyMan.register( "RPCAPTCache", RPCAPTCache )

def get_rpcaptcache(rfs, logpath):
    mm = MyMan()
    mm.start()

    return mm.RPCAPTCache(rfs,logpath)








