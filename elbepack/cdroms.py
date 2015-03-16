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

import os

from apt.package import FetchError
from elbepack.rpcaptcache import get_rpcaptcache
from elbepack.repomanager import CdromSrcRepo
from elbepack.repomanager import CdromBinRepo
from elbepack.aptpkgutils import XMLPackage, APTPackage
from elbepack.aptprogress import ElbeAcquireProgress
from apt import Cache

CDROM_SIZE = 640*1000*1000


def get_initvm_pkglist ():
    cache = Cache ()
    cache.open ()
    pkglist = [APTPackage (p) for p in cache if p.is_installed]
    pkglist.append ( APTPackage( cache ['elbe-bootstrap'] ) )
    return pkglist


def mk_source_cdrom(rfs, arch, codename, target, log):

    rfs.mkdir_p( '/var/cache/elbe/sources' )

    repo = CdromSrcRepo( codename,
                         os.path.join( target, "srcrepo" ),
                         log,
                         CDROM_SIZE )

    cache = get_rpcaptcache( rfs, "aptcache.log", arch )

    pkglist = cache.get_installed_pkgs()

    for pkg in pkglist:
        try:
            dsc = cache.download_source( pkg.name, '/var/cache/elbe/sources' )
            repo.includedsc( dsc )
        except ValueError as ve:
            log.printo( "No sources for Package " + pkg.name + "-" + pkg.installed_version )
        except FetchError as fe:
            log.printo( "Source for Package " + pkg.name + "-" + pkg.installed_version + " could not be downloaded" )

    pkglist = get_initvm_pkglist()
    cache = Cache ()
    cache.open ()

    for pkg in pkglist:
        try:
            p = cache[pkg.name]
            pkgver = p.installed

            dsc = pkgver.fetch_source ('/var/cache/elbe/sources',
                             ElbeAcquireProgress (cb=None), unpack=False)
            repo.includedsc( dsc )
        except ValueError as ve:
            log.printo( "No sources for Package " + pkg.name + "-" + pkg.installed_version )
        except FetchError as fe:
            log.printo( "Source for Package " + pkg.name + "-" + pkg.installed_version + " could not be downloaded" )

    repo.buildiso( os.path.join( target, "src-cdrom.iso" ) )


def mk_binary_cdrom(rfs, arch, codename, xml, target, log):

    rfs.mkdir_p( '/var/cache/elbe/binaries/added' )
    rfs.mkdir_p( '/var/cache/elbe/binaries/main' )

    repo = CdromBinRepo(xml, os.path.join( target, "binrepo" ), log, CDROM_SIZE )

    if not xml is None:
        pkglist = get_initvm_pkglist()
        cache = Cache ()
        cache.open ()
        for pkg in pkglist:
            try:
                p = cache [pkg.name]
                if pkg.name == 'elbe-bootstrap':
                    pkgver = p.versions [0]
                else:
                    pkgver = p.installed
                deb = pkgver.fetch_binary ('/var/cache/elbe/binaries/main',
                                            ElbeAcquireProgress (cb=None) )
                repo.includedeb(deb, 'main')
            except ValueError as ve:
                log.printo( "No Package " + pkg.name + "-" + pkg.installed_version )
            except FetchError as fe:
                log.printo( "Package " + pkg.name + "-" + pkg.installed_version + " could not be downloaded" )
            except TypeError as te:
                log.printo( "Package " + pkg.name + "-" + pkg.installed_version + " missing name or version" )

        cache = get_rpcaptcache( rfs, "aptcache.log", arch )
        for p in xml.node("debootstrappkgs"):
            pkg = XMLPackage(p, arch)
            try:
                deb = cache.download_binary( pkg.name,
                                             '/var/cache/elbe/binaries/main',
                                             pkg.installed_version )
                repo.includedeb(deb, 'main')
            except ValueError as ve:
                log.printo( "No Package " + pkg.name + "-" + pkg.installed_version )
            except FetchError as fe:
                log.printo( "Package " + pkg.name + "-" + pkg.installed_version + " could not be downloaded" )
            except TypeError as te:
                log.printo( "Package " + pkg.name + "-" + pkg.installed_version + " missing name or version" )

    cache = get_rpcaptcache( rfs, "aptcache.log", arch )
    pkglist = cache.get_installed_pkgs ()
    for pkg in pkglist:
        try:
            deb = cache.download_binary( pkg.name,
                                        '/var/cache/elbe/binaries/added',
                                        pkg.installed_version )
            repo.includedeb(deb, 'added')
        except KeyError as ke:
            log.printo( str (ke) )
        except ValueError as ve:
            log.printo( "No Package " + pkg.name + "-" + pkg.installed_version )
        except FetchError as fe:
            log.printo( "Package " + pkg.name + "-" + str (pkg.installed_version) + " could not be downloaded" )
        except TypeError as te:
            log.printo( "Package " + pkg.name + "-" + pkg.installed_version + " missing name or version" )

    repo.buildiso( os.path.join( target, "bin-cdrom.iso" ) )
