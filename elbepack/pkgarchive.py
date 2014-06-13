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
from os import path, remove
from shutil import rmtree, copyfile, copytree, move
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

def checkout_binpkg_archive (ep, repodir):
    repopath = path.join( ep.builddir, repodir )
    sources_list = ep.buildenv.rfs.fname( 'etc/apt/sources.list' )
    sources_list_d = ep.buildenv.rfs.fname( 'etc/apt/sources.list.d' )
    sources_list_backup = path.join( ep.builddir, 'sources.list.orig' )
    sources_list_d_backup = path.join( ep.builddir, 'sources.list.d.orig' )
    pkgarchive = ep.buildenv.rfs.fname( 'var/cache/elbe/pkgarchive' )

    with ep.buildenv:
        try:
            # Copy the package archive into the buildenv, so the RPCAptCache can
            # access it
            ep.log.printo( "Copying package archive into build environment" )
            copytree( repopath, pkgarchive )

            # Move original etc/apt/sources.list and etc/apt/sources.list.d out
            # of the way
            ep.log.printo( "Moving original APT configuration out of the way" )
            if path.isfile( sources_list ):
                move( sources_list, sources_list_backup )
            if path.isdir( sources_list_d ):
                move( sources_list_d, sources_list_d_backup )

            # Now create our own, with the package archive being the only source
            ep.log.printo( "Creating new /etc/apt/sources.list" )
            deb = "deb file:///var/cache/elbe/pkgarchive "
            deb += ep.xml.text( "/project/suite" )
            deb += " main"
            with open( sources_list, 'w' ) as f:
                f.write( deb )

            # We need to update the APT cache to apply the changed package
            # source
            ep.log.printo( "Updating APT cache to use package archive" )
            ep.drop_rpcaptcache()
            c = ep.get_rpcaptcache()
            c.update()

            # Iterate over all packages, and mark them for installation or
            # deletion, using the same logic as in commands/updated.py
            ep.log.printo( "Calculating packages to install/remove" )
            fpl = ep.xml.node( "fullpkgs" )
            pkgs = c.get_pkglist('all')

            for p in pkgs:
                marked = False
                for fpi in fpl:
                    if p.name == fpi.et.text:
                        version = fpi.et.get( 'version' )
                        ep.log.printo( "Install " + p.name + "-" + version )
                        c.mark_install( p.name, version,
                                from_user = not fpi.et.get( 'auto' ),
                                nodeps = True )
                        marked = True

                if not marked:
                    ep.log.printo( "Delete " + p.name + "-" + version )
                    c.mark_delete( p.name, None )

            # Now commit the changes
            ep.log.printo( "Commiting package changes" )
            c.commit()
        finally:
            # If we changed the package sources, move back the backup
            if path.isdir( sources_list_d_backup ) or \
                    path.isfile( sources_list_backup ):
                ep.log.printo( "Moving back original APT configuration" )
                update_needed = True
            else:
                update_needed = False

            if path.isdir( sources_list_d_backup ):
                move( sources_list_d_backup, sources_list_d )

            if path.isfile( sources_list_backup ):
                if path.isfile( sources_list ):
                    remove( sources_list )
                move( sources_list_backup, sources_list )

            # Remove the package archive from the buildenv
            if path.isdir( pkgarchive ):
                ep.log.printo(
                        "Removing package archive from build environment" )
                rmtree( pkgarchive )

            # Update APT cache, if we modified the package sources
            if update_needed:
                ep.log.printo(
                        "Updating APT cache to use original package sources" )
                ep.drop_rpcaptcache()
                ep.get_rpcaptcache().update()
