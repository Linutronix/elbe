#!/usr/bin/env python
#
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

import errno
from os import path
from shutil import rmtree, copyfile
from apt.package import FetchError
from elbepack.repomanager import RepoBase

class ArchiveRepo(RepoBase):
    def __init__( self, xml, path, log, origin, description, components,
            maxsize=None ):
        arch = xml.text( "project/arch", key="arch" )
        codename = xml.text( "project/suite" )

        RepoBase.__init__( self, path, log, arch, codename, origin,
                description, components, maxsize )

def gen_binpkg_archive(ep, repodir):
    repopath = path.join( ep.builddir, repodir )

    try:
        rmtree( repopath )
    except OSError as e:
        if e.errno != errno.ENOENT:
            raise

    # Create archive directory for packages we have to download
    ep.buildenv.rfs.mkdir_p( '/var/cache/elbe/pkgarchive' )

    try:
        # Repository containing all packages currently installed
        repo = ArchiveRepo( ep.xml, repopath, ep.log, "Elbe",
                "Elbe package archive", "main" )

        c = ep.get_rpcaptcache()
        pkglist = c.get_installed_pkgs()

        for pkg in pkglist:
            # Use package from local APT archive, if the file exists
            filename = pkg.installed_deb
            rel_path = path.join( 'var/cache/apt/archives', filename )
            abs_path = ep.buildenv.rfs.fname( rel_path )

            if not path.isfile( abs_path ):
                # Package file does not exist, download it and adjust path name
                ep.log.printo( "Package file " + filename +
                        " not found in var/cache/apt/archives, downloading it" )
                abs_path = ep.buildenv.rfs.fname( rel_path )
                try:
                    abs_path = c.download_binary( pkg.name,
                            '/var/cache/elbe/pkgarchive',
                            pkg.installed_version )
                except ValueError as ve:
                    ep.log.printo( "No Package " + pkg.name + "-" +
                            pkg.installed_version )
                    raise
                except FetchError as fe:
                    ep.log.printo( "Package " + pkg.name + "-" +
                            pkg.installed_version + " could not be downloaded" )
                    raise
                except TypeError as te:
                    ep.log.printo( "Package " + pkg.name + "-" +
                            pkg.installed_version + " missing name or version" )
                    raise

            # Add package to repository
            # XXX Use correct component
            repo.includedeb( abs_path, "main" )
    finally:
        rmtree( ep.buildenv.rfs.fname( 'var/cache/elbe/pkgarchive' ) )
