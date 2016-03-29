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
import io

from elbepack.asciidoclog import ASCIIDocLog, StdoutLog
from elbepack.shellhelper import CommandError
from elbepack.elbexml import ElbeXML, NoInitvmNode, ValidationError
from elbepack.rfs import BuildEnv
from elbepack.rpcaptcache import get_rpcaptcache
from elbepack.efilesystem import TargetFs
from elbepack.efilesystem import extract_target

from elbepack.dump import elbe_report
from elbepack.dump import dump_debootstrappkgs, dump_initvmpkgs, dump_fullpkgs
from elbepack.dump import check_full_pkgs

from elbepack.cdroms import mk_source_cdrom, mk_binary_cdrom

from elbepack.pbuilder import pbuilder_write_config, pbuilder_write_repo_hook, pbuilder_write_apt_conf
from elbepack.repomanager import ProjectRepo

class IncompatibleArchitectureException(Exception):
    def __init__ (self, oldarch, newarch):
        Exception.__init__(self,
            "Cannot change architecture from %s to %s in existing project" %
            (oldarch, newarch) )

class AptCacheUpdateError(Exception):
    def __init__ (self):
        Exception.__init__ (self, "Error Updating rpcaptcache")

class AptCacheCommitError(Exception):
    def __init__ (self):
        Exception.__init__ (self, "Error Committing rpcaptcache")

class ElbeProject (object):
    def __init__ (self, builddir, xmlpath = None, logpath = None, name = None,
            override_buildtype = None, skip_validate = False,
            skip_urlcheck = False, rpcaptcache_notifier = None,
            private_data = None, postbuild_file = None, presh_file = None,
            postsh_file = None, savesh_file = None):
        self.builddir = os.path.abspath(str(builddir))
        self.chrootpath = os.path.join(self.builddir, "chroot")
        self.targetpath = os.path.join(self.builddir, "target")

        self.name = name
        self.override_buildtype = override_buildtype
        self.skip_validate = skip_validate
        self.skip_urlcheck = skip_urlcheck
        self.postbuild_file = postbuild_file
        self.presh_file = presh_file
        self.postsh_file = postsh_file
        self.savesh_file = savesh_file

        self.private_data = private_data

        # Apt-Cache will be created on demand with the specified notifier by
        # the get_rpcaptcache method
        self._rpcaptcache = None
        self.rpcaptcache_notifier = rpcaptcache_notifier

        # Initialise Repo Images to Empty list.
        self.repo_images = []

        # Use supplied XML file, if given, otherwise use the source.xml
        # file of the project
        if xmlpath:
            self.xml = ElbeXML( xmlpath, buildtype=override_buildtype,
                    skip_validate=skip_validate, skip_urlcheck=skip_urlcheck )
        else:
            sourcexmlpath = os.path.join( self.builddir, "source.xml" )
            self.xml = ElbeXML( sourcexmlpath, buildtype=override_buildtype,
                    skip_validate=skip_validate, skip_urlcheck=skip_urlcheck )

        self.arch = self.xml.text( "project/arch", key="arch" )
        self.codename = self.xml.text( "project/suite" )

        # If logpath is given, use an AsciiDocLog instance, otherwise log
        # to stdout
        if logpath:
            self.log = ASCIIDocLog( logpath )
        else:
            self.log = StdoutLog()

        self.repo = ProjectRepo (self.arch, self.codename,
                                 os.path.join(self.builddir, "repo"), self.log)

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

    def build_chroottarball (self):
        self.log.do("tar cJf %s/chroot.tar.xz \
                --exclude=./tmp/*  --exclude=./dev/* \
                --exclude=./run/*  --exclude=./sys/* \
                --exclude=./proc/* --exclude=./var/cache/* \
                -C %s ." % (self.builddir, self.chrootpath))

    def build_sysroot (self):

        debootstrap_pkgs = [p.et.text for p in self.xml.node ("debootstrappkgs")]

        with self.buildenv:
            try:
                self.get_rpcaptcache().mark_install_devpkgs(debootstrap_pkgs)
            except SystemError as e:
                self.log.printo( "mark install devpkgs failed: %s" % str(e) )
            try:
                self.get_rpcaptcache().commit()
            except SystemError:
                self.log.printo( "commiting changes failed" )
                raise AptCacheCommitError ()

        sysrootfilelist = os.path.join(self.builddir, "sysroot-filelist")

        with self.buildenv.rfs:
            self.log.do( "chroot %s /usr/bin/symlinks -cr /usr/lib" %
                         self.chrootpath )

        triplet = self.xml.defs["triplet"]

        paths = [ './usr/include', './usr/include/' + triplet,
                  './opt/*/lib/*.so', '/opt/*lib/*.so.*', './opt/*/include/',
                  './opt/*/lib/' + triplet, './opt/*/include/' + triplet,
                  './lib/*.so', './lib/*.so.*', './lib/' + triplet,
                  './usr/lib/*.so', './usr/lib/*.so', './usr/lib/*.so.*', './usr/lib/' + triplet ]

        self.log.do( "rm %s" % sysrootfilelist, allow_fail=True)

        os.chdir( self.chrootpath )
        for p in paths:
            self.log.do( 'find -path "%s" >> %s' % (p, sysrootfilelist) )

        self.log.do( "tar cvfJ %s/sysroot.tar.xz -C %s -T %s" %
                (self.builddir, self.chrootpath, sysrootfilelist) )

        # chroot is invalid after adding all the -dev packages
        # it shouldn't be used to create an incremental image
        self.log.do( "rm -rf %s" % self.chrootpath )

    def pbuild (self, p):
        self.pdebuild_init ()
        src_path = os.path.join (self.builddir, "pdebuilder", "current")

        self.log.printo ("retrieve pbuild sources: %s" % p.text('.'))
        if p.tag == 'git':
            self.log.do ("git clone %s %s" % (p.text('.'), src_path))
        elif p.tag == 'svn':
            self.log.do ("svn co %s %s" % (p.text('.'), src_path))
        else:
            self.log.printo ("unknown pbuild source vcs: %s" % p.tag)

        self.pdebuild_build ()

    def build (self, skip_debootstrap = False, build_bin = False,
               build_sources = False, cdrom_size = None, debug = False,
               skip_pkglist = False, skip_pbuild = False):

        # Write the log header
        self.write_log_header()

        if (self.xml.has('target/pbuilder') and not skip_pbuild):
            if not os.path.exists ( os.path.join (self.builddir, "pbuilder") ):
                self.create_pbuilder ()
            for p in self.xml.node ('target/pbuilder'):
                self.pbuild (p)
                # the package might be needed by a following pbuild, so update
                # the project repo that it can be installed in as
                # build-dependency
                self.repo.finalize ()

        # To avoid update cache errors, the project repo needs to have
        # Release and Packages files, even if it's empty. So don't do this
        # in the if case above!
        self.repo.finalize ()

        # Create the build environment, if it does not exist yet
        if not self.buildenv:
            self.log.do( 'mkdir -p "%s"' % self.chrootpath )
            self.buildenv = BuildEnv( self.xml, self.log, self.chrootpath,
                                      build_sources = build_sources )
            skip_pkglist = False

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

            self.xml.dump_elbe_version ()

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
        elbe_report( self.xml, self.buildenv, self.get_rpcaptcache(),
                reportpath, self.targetfs )

        # Licenses
        f = io.open( os.path.join( self.builddir, "licence.txt" ), "w+", encoding='utf-8' )
        self.buildenv.rfs.write_licenses(f, self.log, os.path.join( self.builddir, "licence.xml"))
        f.close()

        # Use some handwaving to determine grub version
        # jessie and wheezy grubs are 2.0 but differ in behaviour
        #
        # We might also want support for legacy grub
        if self.get_rpcaptcache().is_installed( 'grub-pc' ):
            if self.codename == "jessie":
                grub_version = 202
            else:
                grub_version = 199
        elif self.get_rpcaptcache().is_installed( 'grub-legacy' ):
            self.log.printo( "package grub-legacy is installed, this is obsolete, skipping grub" )
            grub_version = 0
        else:
            self.log.printo( "package grub-pc is not installed, skipping grub" )
            # version 0 == skip_grub
            grub_version = 0
        self.targetfs.part_target( self.builddir, grub_version )

        # Build cdrom images
        self.repo_images = []
        with self.buildenv:
            init_codename = self.xml.get_initvm_codename()
            if build_bin:
                self.repo_images += mk_binary_cdrom( self.buildenv.rfs,
                                                     self.arch,
                                                     self.codename,
                                                     init_codename,
                                                     self.xml,
                                                     self.builddir,
                                                     self.log,
                                                     cdrom_size=cdrom_size )
            if build_sources:
                try:
                    self.repo_images += mk_source_cdrom(self.buildenv.rfs,
                                                        self.arch,
                                                        self.codename,
                                                        init_codename,
                                                        self.builddir,
                                                        self.log,
                                                        cdrom_size=cdrom_size )
                except SystemError as e:
                    # e.g. no deb-src urls specified
                    self.log.printo( str (e) )


        if self.postbuild_file:
            self.log.h2 ("postbuild script:")
            self.log.do (self.postbuild_file + ' "%s %s %s"' % (
                            self.builddir,
                            self.xml.text ("project/version"),
                            self.xml.text ("project/name")),
                         allow_fail=True)

        os.system( 'cat "%s"' % os.path.join( self.builddir, "validation.txt" ) )

    def pdebuild_init (self):
        # Remove pdebuilder directory, containing last build results
        self.log.do ('rm -rf "%s"' % os.path.join (self.builddir,
                                                   "pdebuilder"))

        # Remove pbuilder/result directory
        self.log.do ('rm -rf "%s"' % os.path.join (self.builddir,
                                                   "pbuilder", "result"))

        # Recreate the directories removed
        self.log.do ('mkdir -p "%s"' % os.path.join (self.builddir,
                                                     "pbuilder", "result"))

    def pdebuild (self):
        self.pdebuild_init ()

        self.log.do ('mkdir -p "%s"' % os.path.join (self.builddir,
                                                     "pdebuilder", "current"))

        # Untar current_pdebuild.tar.gz into pdebuilder/current
        self.log.do ('tar xvfz "%s" -C "%s"' % (os.path.join (self.builddir,
                                                  "current_pdebuild.tar.gz"),
                                                os.path.join (self.builddir,
                                                  "pdebuilder", "current")))

        self.pdebuild_build ()
        self.repo.finalize ()


    def pdebuild_build (self):
        try:
            self.log.do ('cd "%s"; pdebuild --debbuildopts -jauto --configfile "%s" --use-pdebuild-internal --buildresult "%s"' % (
                os.path.join (self.builddir, "pdebuilder", "current"),
                os.path.join (self.builddir, "pbuilderrc"),
                os.path.join (self.builddir, "pbuilder", "result")))
        except CommandError as e:
            self.log.printo ('')
            self.log.printo ('Package fails to build.')
            self.log.printo ('Please make sure, that the submitted package builds in pbuilder')

        self.repo.include (os.path.join (self.builddir,
            "pbuilder", "result", "*.changes"))

    def create_pbuilder (self):
        # Remove old pbuilder directory, if it exists
        self.log.do ('rm -rf "%s"' % os.path.join (self.builddir, "pbuilder"))

        # make hooks.d and pbuilder directory
        self.log.do ('mkdir -p "%s"' % os.path.join (self.builddir, "pbuilder", "hooks.d"))
        self.log.do ('mkdir -p "%s"' % os.path.join (self.builddir, "aptconfdir", "apt.conf.d"))

        # write config files
        pbuilder_write_config (self.builddir, self.xml, self.log)
        pbuilder_write_apt_conf (self.builddir, self.xml)
        pbuilder_write_repo_hook (self.builddir, self.xml)
        self.log.do ('chmod 755 "%s"' % os.path.join (self.builddir, "pbuilder", "hooks.d", "D10elbe_apt_sources"))

        # Run pbuilder --create
        self.log.do ('pbuilder --create --configfile "%s" --aptconfdir "%s" --extrapackages git' % (
                     os.path.join (self.builddir, "pbuilderrc"), os.path.join (self.builddir, "aptconfdir")))

    def sync_xml_to_disk (self):
        try:
            sourcexmlpath = os.path.join( self.builddir, "source.xml" )
            self.xml.xml.write( sourcexmlpath )
        except MemoryError:
            self.log.printo( "write source.xml failed (archive to huge?)" )

    def get_rpcaptcache (self):
        if self._rpcaptcache is None:
            self._rpcaptcache = get_rpcaptcache( self.buildenv.rfs,
                    "aptcache.log",
                    self.arch,
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
                skip_validate=self.skip_validate,
                skip_urlcheck=self.skip_urlcheck )

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
                raise AptCacheUpdateError ()

            # Then dump the debootstrap packages
            if self.buildenv.fresh_debootstrap:
                if self.buildenv.need_dumpdebootstrap:
                    dump_debootstrappkgs (self.xml, self.get_rpcaptcache ())
                    dump_initvmpkgs (self.xml)
                self.buildenv.need_dumpdebootstrap = False
                source = self.xml
                try:
                    initxml = ElbeXML( "/var/cache/elbe/source.xml",
                            skip_validate=self.skip_validate, skip_urlcheck=True )
                    self.xml.get_initvmnode_from( initxml )
                except ValidationError as e:
                    self.log.printo( "/var/cache/elbe/source.xml validation failed" )
                    self.log.printo( str(e) )
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
                        skip_validate=self.skip_validate,
                        skip_urlcheck=self.skip_urlcheck )

                self.xml.get_debootstrappkgs_from( source )
                try:
                    self.xml.get_initvmnode_from( source )
                except NoInitvmNode:
                    self.log.printo( "source.xml is available" )
                    self.log.printo( "But it does not contain an initvm node" )

            # Seed /etc, we need /etc/hosts for hostname -f to work correctly
            if not buildenv:
                self.buildenv.seed_etc()

            # remove all non-essential packages to ensure that on a incremental
            # build packages can be removed
            debootstrap_pkgs = []
            for p in self.xml.node("debootstrappkgs"):
                debootstrap_pkgs.append (p.et.text)

            pkgs = self.buildenv.xml.get_target_packages()

            if buildenv:
                pkgs = pkgs + self.buildenv.xml.get_buildenv_packages()

            # Now install requested packages
            for p in pkgs:
                try:
                    self.get_rpcaptcache().mark_install( p, None )
                except KeyError:
                    self.log.printo( "No Package " + p )
                except SystemError:
                    self.log.printo( "Unable to correct problems " + p )

            # temporary disabled because of
            # https://bugs.debian.org/cgi-bin/bugreport.cgi?bug=776057
            # the functions cleans up to much
            # self.get_rpcaptcache().cleanup(debootstrap_pkgs + pkgs)

            try:
                self.get_rpcaptcache().commit()
            except SystemError:
                self.log.printo( "commiting changes failed" )
                raise AptCacheCommitError ()
