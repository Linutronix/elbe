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

from elbepack.asciidoclog import ASCIIDocLog, StdoutLog
from elbepack.elbexml import ElbeXML, NoInitvmNode, ValidationError
from elbepack.rfs import BuildEnv
from elbepack.rpcaptcache import get_rpcaptcache
from elbepack.filesystem import TargetFs
from elbepack.filesystem import extract_target
from elbepack.dump import elbe_report, dump_debootstrappkgs
from elbepack.dump import dump_fullpkgs, check_full_pkgs
from elbepack.cdroms import mk_source_cdrom, mk_binary_cdrom

class IncompatibeArchitectureException(Exception):
    def __init__ (self, oldarch, newarch):
        Exception.__init__(self,
            "Cannot change architecture from %s to %s in existing project" %
            (oldarch, newarch) )

class ElbeProject (object):
    def __init__ (self, builddir, xmlpath = None, logpath = None, name = None,
            override_buildtype = None, skip_validate = False,
            rpcaptcache_notifier = None, private_data = None,
            presh_file = None, postsh_file = None):
        self.builddir = os.path.abspath(builddir)
        self.chrootpath = os.path.join(self.builddir, "chroot")
        self.targetpath = os.path.join(self.builddir, "target")

        self.name = name
        self.override_buildtype = override_buildtype
        self.skip_validate = skip_validate
        self.presh_file = presh_file
        self.postsh_file = postsh_file

        self.private_data = private_data

        # Apt-Cache will be created on demand with the specified notifier by
        # the get_rpcaptcache method
        self._rpcaptcache = None
        self.rpcaptcache_notifier = rpcaptcache_notifier

        # Use supplied XML file, if given, otherwise use the source.xml
        # file of the project
        if xmlpath:
            self.xml = ElbeXML( xmlpath, buildtype=override_buildtype,
                    skip_validate=skip_validate )
        else:
            sourcexmlpath = os.path.join( self.builddir, "source.xml" )
            self.xml = ElbeXML( sourcexmlpath, buildtype=override_buildtype,
                    skip_validate=skip_validate )

        # If logpath is given, use an AsciiDocLog instance, otherwise log
        # to stdout
        if logpath:
            self.log = ASCIIDocLog( logpath )
        else:
            self.log = StdoutLog()

        # Create BuildEnv instance, if the chroot directory exists and
        # has an etc/elbe_version
        if self.has_full_buildenv():
            self.buildenv = BuildEnv( self.xml, self.log, self.chrootpath )
        else:
            self.buildenv = None
            self.targetfs = None
            return

        # Create TargetFs instance, if the target directory exists
        if os.path.exists( self.targetpath ):
            self.targetfs = TargetFs( self.targetpath, self.log,
                    self.buildenv.xml, clean=False )
        else:
            self.targetfs = None

    def build (self, skip_debootstrap = False, skip_cdrom = False,
            build_sources = False, debug = False, skip_pkglist = False):
        # Write the log header
        self.write_log_header()

        # Create the build environment, if it does not exist yet
        if not self.buildenv:
            self.log.do( 'mkdir -p "%s"' % self.chrootpath )
            self.buildenv = BuildEnv( self.xml, self.log, self.chrootpath )

        # Install packages
        if not skip_pkglist:
            self.install_packages()

        try:
            self.buildenv.rfs.dump_elbeversion (self.xml)
        except IOError:
            self.log.printo ("dump elbeversion failed")

        # Extract target FS. We always create a new instance here with
        # clean=true, because we want a pristine directory.
        self.targetfs = TargetFs( self.targetpath, self.log,
                self.buildenv.xml, clean=True )
        os.chdir( self.buildenv.rfs.fname( '' ) )
        extract_target( self.buildenv.rfs, self.xml, self.targetfs,
                self.log, self.get_rpcaptcache() )

        # Package validation and package list
        if not skip_pkglist:
            validationpath = os.path.join( self.builddir, "validation.txt" )
            pkgs = self.xml.xml.node( "/target/pkg-list" )
            if self.xml.has( "fullpkgs" ):
                check_full_pkgs( pkgs, self.xml.xml.node( "/fullpkgs" ),
                        validationpath, self.get_rpcaptcache() )
            else:
                check_full_pkgs( pkgs, None, validationpath,
                        self.get_rpcaptcache() )
            dump_fullpkgs( self.xml, self.buildenv.rfs, self.get_rpcaptcache() )

        self.targetfs.write_fstab (self.xml )

        # Dump ELBE version
        try:
            self.targetfs.dump_elbeversion( self.xml )
        except MemoryError:
            self.log.printo( "dump elbeversion failed" )

        # install packages for buildenv
        if not skip_pkglist:
            self.install_packages(buildenv=True)

        # Write source.xml
        try:
            sourcexmlpath = os.path.join( self.builddir, "source.xml" )
            self.xml.xml.write( sourcexmlpath )
        except MemoryError:
            self.log.printo( "write source.xml failed (archive to huge?)" )

        # Elbe report
        reportpath = os.path.join( self.builddir, "elbe-report.txt" )
        elbe_report( self.xml, self.buildenv.rfs, self.get_rpcaptcache(),
                reportpath, self.targetfs )

        # Licenses
        f = open( os.path.join( self.builddir, "licence.txt" ), "w+" )
        self.buildenv.rfs.write_licenses(f, self.log)
        f.close()

        # Generate images
        if self.get_rpcaptcache().is_installed( 'grub-pc' ):
            grub_version = 2

        elif self.get_rpcaptcache().is_installed( 'grub-legacy' ):
            grub_version = 1
        else:
            self.log.printo( "package grub-pc is not installed, skipping grub" )
            # version 0 == skip_grub
            grub_version = 0
        self.targetfs.part_target( self.builddir, grub_version )

        # Build cdrom images
        arch = self.xml.text( "project/arch", key="arch" )
        codename = self.xml.text( "project/suite" )
        with self.buildenv:
            if not skip_cdrom:
                mk_binary_cdrom( self.buildenv.rfs, arch, codename, self.xml,
                        self.builddir, self.log )
                if build_sources:
                    mk_source_cdrom( self.buildenv.rfs, arch, codename,
                            self.builddir, self.log )

        # Write files to extract list
        fte = open( os.path.join( self.builddir, "files-to-extract" ), "w+" )
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

        os.system( 'cat "%s"' % os.path.join( self.builddir, "validation.txt" ) )

    def get_rpcaptcache (self):
        if self._rpcaptcache is None:
            self._rpcaptcache = get_rpcaptcache( self.buildenv.rfs,
                    "aptcache.log",
                    self.xml.text( "project/arch", key="arch" ),
                    self.rpcaptcache_notifier )
        return self._rpcaptcache

    def drop_rpcaptcache (self):
        self._rpcaptcache = None;

    def has_full_buildenv (self):
        if os.path.exists( self.chrootpath ):
            elbeversionpath = os.path.join( self.chrootpath,
                    "etc", "elbe_version" )
            if os.path.isfile( elbeversionpath ):
                return True
            else:
                self.log.printo( "%s exists, but it does not have an etc/elbe_version file." %
                        self.chrootpath )
                # Apparently we do not have a functional build environment
                return False
        else:
            return False

    def set_xml (self, xmlpath):
        # Use supplied XML file, if given, otherwise change to source.xml
        if not xmlpath:
            xmlpath = os.path.join( self.builddir, "source.xml" )

        newxml = ElbeXML( xmlpath, buildtype=self.override_buildtype,
                skip_validate=self.skip_validate )

        # New XML file has to have the same architecture
        oldarch = self.xml.text( "project/arch", key="arch" )
        newarch = newxml.text( "project/arch", key="arch" )
        if newarch != oldarch:
            raise IncompatibleArchitectureException( oldarch, newarch )

        # Throw away old APT cache, targetfs and buildenv
        self._rpcaptcache = None
        self.targetfs = None
        self.buildenv = None

        self.xml = newxml

        # Create a new BuildEnv instance, if we have a build directory
        if self.has_full_buildenv():
            self.buildenv = BuildEnv( self.xml, self.log, self.chrootpath )

        # Create TargetFs instance, if the target directory exists.
        # We use the old content of the directory if no rebuild is done, so
        # don't clean it (yet).
        if os.path.exists( self.targetpath ):
            self.targetfs = TargetFs( self.targetpath, self.log,
                    self.buildenv.xml, clean=False )
        else:
            self.targetfs = None

    def write_log_header (self):
        if self.name:
            self.log.h1( "ELBE Report for Project " + self.name)
        else:
            self.log.h1( "ELBE Report" )
        self.log.printo( "report timestamp: " +
                datetime.datetime.now().strftime("%Y%m%d-%H%M%S") )

    def install_packages (self, buildenv=False):
        with self.buildenv:
            # First update the apt cache
            try:
                self.get_rpcaptcache().update()
            except:
                self.log.printo( "update cache failed" )

            # Then dump the debootstrap packages
            if self.buildenv.fresh_debootstrap:
                if self.buildenv.need_dumpdebootstrap:
                    dump_debootstrappkgs( self.xml, self.get_rpcaptcache() )
                self.buildenv.need_dumpdebootstrap = False
                source = self.xml
                try:
                    initxml = ElbeXML( "/var/cache/elbe/source.xml",
                            skip_validate=self.skip_validate )
                    self.xml.get_initvmnode_from( initxml )
                except ValidationError:
                    self.log.printo( "/var/cache/elbe/source.xml validation failed" )
                    self.log.printo( "will not copy initvm node" )
                except IOError:
                    self.log.printo( "/var/cache/elbe/source.xml not available" )
                    self.log.printo( "can not copy initvm node" )
                except NoInitvmNode:
                    self.log.printo( "/var/cache/elbe/source.xml is available" )
                    self.log.printo( "But it does not contain an initvm node" )
            else:
                sourcepath = os.path.join( self.builddir, "source.xml" )
                source = ElbeXML( sourcepath,
                        buildtype=self.override_buildtype,
                        skip_validate=self.skip_validate )

                self.xml.get_debootstrappkgs_from( source )
                try:
                    self.xml.get_initvmnode_from( source )
                except NoInitvmNode:
                    self.log.printo( "source.xml is available" )
                    self.log.printo( "But it does not contain an initvm node" )

            # Seed /etc, we need /etc/hosts for hostname -f to work correctly
            self.buildenv.seed_etc()

            # remove all non-essential packages to ensure that on a incremental
            # build packages can be removed
            debootstrap_pkgs = []
            for p in self.xml.node("debootstrappkgs"):
                debootstrap_pkgs.append (p.et.text)

            self.get_rpcaptcache().cleanup(debootstrap_pkgs)

            # Now install requested packages
            pkgs = self.buildenv.xml.get_target_packages()

            if buildenv:
                pkgs = pkgs + self.buildenv.xml.get_buildenv_packages()

            for p in pkgs:
                try:
                    self.get_rpcaptcache().mark_install( p, None )
                except KeyError:
                    self.log.printo( "No Package " + p )
                except SystemError:
                    self.log.printo( "Unable to correct problems " + p )
            try:
                self.get_rpcaptcache().commit()
            except SystemError:
                self.log.printo( "commiting changes failed" )
