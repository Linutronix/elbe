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
from elbepack.filesystem import Filesystem
from apt import Cache

CDROM_SIZE = 640*1000*1000

hostfs = Filesystem( "/" )

def get_initvm_pkglist ():
    cache = Cache ()
    cache.open ()
    pkglist = [APTPackage (p) for p in cache if p.is_installed]
    pkglist.append ( APTPackage( cache ['elbe-bootstrap'] ) )
    return pkglist


def mk_source_cdrom(rfs, arch, codename, init_codename, target, log, cdrom_size=CDROM_SIZE):

    hostfs.mkdir_p( '/var/cache/elbe/sources' )
    rfs.mkdir_p( '/var/cache/elbe/sources' )

    repo = CdromSrcRepo( codename, init_codename,
                         os.path.join( target, "srcrepo" ),
                         log,
                         cdrom_size )

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
            if pkg.name == 'elbe-bootstrap':
                pkgver = p.versions [0]
            else:
                pkgver = p.installed

            dsc = pkgver.fetch_source ('/var/cache/elbe/sources',
                             ElbeAcquireProgress (cb=None), unpack=False)
            repo.includedsc( dsc )
        except ValueError as ve:
            log.printo( "No sources for Package " + pkg.name + "-" + str(pkg.installed_version) )
        except FetchError as fe:
            log.printo( "Source for Package " + pkg.name + "-" + pkgver.version + " could not be downloaded" )

    return repo.buildiso( os.path.join( target, "src-cdrom.iso" ) )


def mk_binary_cdrom(rfs, arch, codename, init_codename, xml, target, log, cdrom_size=CDROM_SIZE):

    rfs.mkdir_p( '/var/cache/elbe/binaries/added' )
    rfs.mkdir_p( '/var/cache/elbe/binaries/main' )
    hostfs.mkdir_p( '/var/cache/elbe/binaries/main' )

    if not xml is None:
        mirror = xml.get_primary_mirror (rfs.fname("cdrom"))
    else:
        mirror='http://ftp.debian.org/debian'

    repo_path = os.path.join (target, "binrepo")

    repo = CdromBinRepo (arch, codename, init_codename,
                         repo_path, log, cdrom_size, mirror)

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
                repo.include_init_deb(deb, 'main')
            except ValueError as ve:
                log.printo( "No Package " + pkg.name + "-" + str(pkg.installed_version) )
            except FetchError as fe:
                log.printo( "Package " + pkg.name + "-" + pkgver.version + " could not be downloaded" )
            except TypeError as te:
                log.printo( "Package " + pkg.name + "-" + str(pkg.installed_version) + " missing name or version" )

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

    # Mark the binary repo with the necessary Files
    # to make the installer accept this as a CDRom
    repo_fs = Filesystem( repo_path )
    repo_fs.mkdir_p (".disk")
    repo_fs.write_file (".disk/base_installable", 0644, "main\n")
    repo_fs.write_file (".disk/base_components", 0644, "main\n")
    repo_fs.write_file (".disk/cd_type", 0644, "not_complete\n")
    repo_fs.write_file (".disk/info", 0644, "elbe inst cdrom - full cd\n")
    repo_fs.symlink (".", "debian", allow_exists=True)
    repo_fs.write_file ("md5sum.txt", 0644, "")

    return repo.buildiso( os.path.join( target, "bin-cdrom.iso" ) )
