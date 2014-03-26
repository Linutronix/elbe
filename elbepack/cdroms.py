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

from apt.package import FetchError
from elbepack.rpcaptcache import get_rpcaptcache
from elbepack.repomanager import CdromSrcRepo
from elbepack.repomanager import CdromBinRepo

def mk_source_cdrom(rfs, arch, codename):

    rfs.mkdir_p( '/opt/elbe/sources' )

    with rfs:
        cache = get_rpcaptcache( rfs, "aptcache.log", arch )

        pkglist = cache.get_installed_pkgs()

        for pkg in pkglist:
            try:
                cache.download_source( pkg.name, '/opt/elbe/sources' )
            except ValueError as ve:
                log.printo( "No sources for Package " + pkg.name + "-" + pkg.installed_version )
            except FetchError as fe:
                log.printo( "Source for Package " + pkg.name + "-" + pkg.installed_version + " could not be downloaded" )

    repo = CdromSrcRepo(codename, "srcrepo" )

    for dsc in rfs.glob('opt/elbe/sources/*.dsc'):
        repo.includedsc(dsc)

def mk_binary_cdrom(rfs, arch, codename):

    rfs.mkdir_p( '/opt/elbe/binaries' )

    with rfs:
        cache = get_rpcaptcache( rfs, "aptcache.log", arch )

        pkglist = cache.get_installed_pkgs()

        for pkg in pkglist:
            try:
                cache.download_binary( pkg.name, '/opt/elbe/binaries' )
            except ValueError as ve:
                log.printo( "No sources for Package " + pkg.name + "-" + pkg.installed_version )
            except FetchError as fe:
                log.printo( "Source for Package " + pkg.name + "-" + pkg.installed_version + " could not be downloaded" )

    repo = CdromBinRepo(codename, "binrepo" )

    for deb in rfs.glob('opt/elbe/binaries/*.deb'):
        repo.includedeb(dsc)
