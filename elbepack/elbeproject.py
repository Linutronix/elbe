#!/usr/bin/env python
#
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
import datetime

from elbepack.elbexml import ElbeXML, NoInitvmNode
from elbepack.rfs import BuildEnv
from elbepack.rpcaptcache import get_rpcaptcache
from elbepack.filesystem import TargetFs
from elbepack.filesystem import extract_target
from elbepack.dump import elbe_report, dump_debootstrappkgs
from elbepack.dump import dump_fullpkgs, check_full_pkgs 
from elbepack.cdroms import mk_source_cdrom, mk_binary_cdrom

class ElbeProject ():
    def __init__ (self, xml, targetpath, log, name = None,
            override_buildtype = None):
        self.xml = xml
        self.targetpath = os.path.abspath(targetpath)
        self.log = log
        self.name = name
        self.override_buildtype = override_buildtype
        self.buildenv = None
        self.targetfs = None

    def build (self, skip_debootstrap = False, skip_cdrom = False,
            build_sources = False, skip_validate = False, debug = False):
        # Write the log header
        self.write_log_header()

        # Create the build environment
        chroot_path = os.path.join( self.targetpath, "chroot" )
        self.buildenv = self.create_buildenv( chroot_path )

        # Install packages
        cache = self.install_packages( skip_validate )

        # Extract target FS
        targetfspath = os.path.join( self.targetpath, "target" )
        self.targetfs = TargetFs( targetfspath, self.log, self.buildenv.xml )
        os.chdir( self.buildenv.rfs.fname( '' ) )
        extract_target( self.buildenv.rfs, self.xml, self.targetfs,
                self.log, cache )

        # Package validation and package list
        validationpath = os.path.join( self.targetpath, "validation.txt" )
        pkgs = self.xml.xml.node( "/target/pkg-list" )
        if self.xml.has( "fullpkgs" ):
            check_full_pkgs( pkgs, self.xml.xml.node( "/fullpkgs" ),
                    validationpath, cache )
        else:
            check_full_pkgs( pkgs, None, validationpath, cache )
        dump_fullpkgs( self.xml, self.buildenv.rfs, cache )

        # Dump ELBE version
        try:
            self.targetfs.dump_elbeversion( self.xml )
        except MemoryError:
            self.log.printo( "dump elbeversion failed" )

        # Write source.xml
        try:
            sourcexmlpath = os.path.join( self.targetpath, "source.xml" )
            self.xml.xml.write( sourcexmlpath )
        except MemoryError:
            self.log.printo( "write source.xml failed (archive to huge?)" )

        # Elbe report
        reportpath = os.path.join( self.targetpath, "elbe-report.txt" )
        elbe_report( self.xml, self.buildenv.rfs, cache, reportpath,
                self.targetfs )

        # Licenses
        f = open( os.path.join( self.targetpath, "licence.txt" ), "w+" )
        self.buildenv.rfs.write_licenses(f, self.log)
        f.close()

        # Generate images
        if cache.is_installed( 'grub-pc' ):
            skip_grub = False
        else:
            self.log.printo( "package grub-pc is not installed, skipping grub" )
            skip_grub = True
        self.targetfs.part_target( self.targetpath, skip_grub )

        # Build cdrom images
        arch = self.xml.text( "project/arch", key="arch" )
        codename = self.xml.text( "project/suite" )
        with self.buildenv:
            if not skip_cdrom:
                mk_binary_cdrom( self.buildenv.rfs, arch, codename, self.xml,
                        self.targetpath, self.log )
                if build_sources:
                    mk_source_cdrom( self.buildenv.rfs, arch, codename,
                            self.targetpath, self.log )

        # Write files to extract list
        fte = open( os.path.join( self.targetpath, "files-to-extract" ), "w+" )
        # store each image only once
        files = set( self.targetfs.images )
        for img in files:
            fte.write(img + '\n')
        fte.write("source.xml\n")
        fte.write("licence.txt\n")
        fte.write("validation.txt\n")
        fte.write("elbe-report.txt\n")
        fte.write("../elbe-report.log\n")
        fte.close()

    def write_log_header (self):
        if self.name:
            self.log.h1( "ELBE Report for Project " + self.name)
        else:
            self.log.h1( "ELBE Report" )
        self.log.printo( "report timestamp: " +
                datetime.datetime.now().strftime("%Y%m%d-%H%M%S") )

    def create_buildenv (self, chroot_path):
        self.log.do( 'mkdir -p "%s"' % chroot_path )
        return BuildEnv( self.xml, self.log, chroot_path )

    def install_packages (self, skip_validation):
        with self.buildenv:
            cache = get_rpcaptcache( self.buildenv.rfs, "aptcache.log",
                    self.xml.text( "project/arch", key="arch" ) )

            # First update the apt cache
            try:
                cache.update()
            except:
                self.log.printo( "update cache failed" )

            # Then dump the debootstrap packages
            if self.buildenv.fresh_debootstrap:
                dump_debootstrappkgs( self.xml, cache )
                source = self.xml
                try:
                    initxml = ElbeXML( "/opt/elbe/source.xml",
                            skip_validate = skip_validation )
                    self.xml.get_initvmnode_from( initxml )
                except IOError:
                    self.log.printo( "/opt/elbe/source.xml not available" )
                    self.log.printo( "can not copy initvm node" )
                except NoInitvmNode:
                    self.log.printo( "/opt/elbe/source.xml is available" )
                    self.log.printo( "But it does not contain an initvm node" )
            else:
                sourcepath = os.path.join( self.targetpath, "source.xml" )
                source = ElbeXML( sourcepath,
                        buildtype=self.override_buildtype,
                        skip_validate=skip_validation )
                self.xml.get_debootstrappkgs_from( source )
                try:
                    self.xml.get_initvmnode_from( source )
                except NoInitvmNode:
                    self.log.printo( "source.xml is available" )
                    self.log.printo( "But it does not contain an initvm node" )

            # Seed /etc, we need /etc/hosts for hostname -f to work correctly
            self.buildenv.seed_etc()

            # Now install packages from all sources
            be_pkgs = self.buildenv.xml.get_buildenv_packages()
            ta_pkgs = self.buildenv.xml.get_target_packages()

            for p in be_pkgs + ta_pkgs:
                try:
                    cache.mark_install( p, None )
                except KeyError:
                    self.log.printo( "No Package " + p )
                except SystemError:
                    self.log.printo( "Unable to correct problems " + p )
            try:
                cache.commit()
            except SystemError:
                self.log.printo( "commiting changes failed" )

        return cache
