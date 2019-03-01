# ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (c) 2014-2018 Manuel Traut <manut@linutronix.de>
# Copyright (c) 2014-2016 Torben Hohn <torben.hohn@linutronix.de>
# Copyright (c) 2014 Stefan Gast <stefan.gast@linutronix.de>
# Copyright (c) 2016-2018 John Ogness <jogness@linutronix.de>
# Copyright (c) 2017 Philipp Arras <philipp.arras@linutronix.de>
# Copyright (c) 2018 Martin Kaistra <martin.kaistra@linutronix.de>
#
# SPDX-License-Identifier: GPL-3.0-or-later

import sys
import os
import datetime
import io

from elbepack.asciidoclog import ASCIIDocLog, StdoutLog
from elbepack.shellhelper import CommandError

from elbepack.elbexml import (ElbeXML, NoInitvmNode,
                              ValidationError, ValidationMode)

from elbepack.rfs import BuildEnv
from elbepack.rpcaptcache import get_rpcaptcache
from elbepack.efilesystem import TargetFs
from elbepack.efilesystem import extract_target

from elbepack.dump import elbe_report
from elbepack.dump import dump_debootstrappkgs, dump_initvmpkgs, dump_fullpkgs
from elbepack.dump import check_full_pkgs

from elbepack.cdroms import mk_source_cdrom, mk_binary_cdrom

from elbepack.pbuilder import (pbuilder_write_config, pbuilder_write_repo_hook,
                               pbuilder_write_apt_conf)

from elbepack.repomanager import ProjectRepo
from elbepack.config import cfg
from elbepack.pkgutils import extract_pkg
from elbepack.templates import write_pack_template
from elbepack.finetuning import do_prj_finetuning


class IncompatibleArchitectureException(Exception):
    def __init__(self, oldarch, newarch):
        Exception.__init__(
            self,
            "Cannot change architecture from %s to %s in existing project" %
            (oldarch, newarch))


class AptCacheUpdateError(Exception):
    def __init__(self, e):
        Exception.__init__(self, "Error Updating rpcaptcache: " + str(e))


class AptCacheCommitError(Exception):
    def __init__(self, msg=''):
        Exception.__init__(self, "Error Committing rpcaptcache %s" % msg)


class UnsupportedSDKException(Exception):
    def __init__(self, triplet):
        Exception.__init__(self, "SDK for %s currently unsupported" % triplet)


def test_gen_sdk_scripts():
    os.system("mkdir -p /tmp/test/sdk")
    gen_sdk_scripts('armhf-linux-gnueabihf',
                    'testproject',
                    '08.15',
                    '/tmp/test',
                    '/tmp/test/sdk')


def gen_sdk_scripts(triplet, prj_name, prj_version, builddir, sdkpath):

    prj_name = prj_name.replace(" ", "_")
    prj_version = prj_version.replace(" ", "_")

    # generate the setup script
    sdkvalues = {'sdk_arch': 'x86_64',
                 'sdk_gcc_ver': '',
                 'sdk_path': '/opt/elbe-sdk-%s-%s-%s' % (triplet,
                                                         prj_name,
                                                         prj_version),
                 'sdk_ext_path': '~/elbe-sdk',
                 'real_multimach_target_sys': triplet,
                 'sdk_title': 'ELBE %s' % prj_name,
                 'sdk_version': prj_version}

    sdkname = 'setup-elbe-sdk-%s-%s-%s.sh' % (triplet, prj_name, prj_version)
    write_pack_template(os.path.join(builddir, sdkname),
                        'toolchain-shar-extract.sh.mako',
                        sdkvalues)
    envname = 'environment-setup-elbe-%s-%s-%s' % (triplet,
                                                   prj_name,
                                                   prj_version)
    write_pack_template(os.path.join(sdkpath, envname),
                        'environment-setup-elbe.mako',
                        sdkvalues)

    return sdkname


class ElbeProject (object):

    # pylint: disable=too-many-instance-attributes

    def __init__(
            self,
            builddir,
            xmlpath=None,
            logpath=None,
            name=None,
            override_buildtype=None,
            skip_validate=False,
            url_validation=ValidationMode.CHECK_ALL,
            rpcaptcache_notifier=None,
            private_data=None,
            postbuild_file=None,
            presh_file=None,
            postsh_file=None,
            savesh_file=None):

        # pylint: disable=too-many-arguments

        self.builddir = os.path.abspath(str(builddir))
        self.chrootpath = os.path.join(self.builddir, "chroot")
        self.targetpath = os.path.join(self.builddir, "target")
        self.sysrootpath = os.path.join(self.builddir, "sysroot")
        self.sdkpath = os.path.join(self.builddir, "sdk")
        self.validationpath = os.path.join(self.builddir, "validation.txt")

        self.name = name
        self.override_buildtype = override_buildtype
        self.skip_validate = skip_validate
        self.url_validation = url_validation
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

        self.orig_fname = None
        self.orig_files = []

        # Use supplied XML file, if given, otherwise use the source.xml
        # file of the project
        if xmlpath:
            self.xml = ElbeXML(
                xmlpath,
                buildtype=override_buildtype,
                skip_validate=skip_validate,
                url_validation=url_validation)
        else:
            sourcexmlpath = os.path.join(self.builddir, "source.xml")
            self.xml = ElbeXML(
                sourcexmlpath,
                buildtype=override_buildtype,
                skip_validate=skip_validate,
                url_validation=url_validation)

        self.arch = self.xml.text("project/arch", key="arch")
        self.codename = self.xml.text("project/suite")

        if not self.name:
            self.name = self.xml.text("project/name")

        # If logpath is given, use an AsciiDocLog instance, otherwise log
        # to stdout
        if logpath:
            self.log = ASCIIDocLog(logpath)
        else:
            self.log = StdoutLog()

        self.repo = ProjectRepo(self.arch, self.codename,
                                os.path.join(self.builddir, "repo"), self.log)

        # Create BuildEnv instance, if the chroot directory exists and
        # has an etc/elbe_version
        if os.path.exists(self.chrootpath):
            self.buildenv = BuildEnv(
                self.xml, self.log, self.chrootpath, clean=False)
        else:
            self.buildenv = None

        # Create TargetFs instance, if the target directory exists
        if os.path.exists(self.targetpath) and self.buildenv:
            self.targetfs = TargetFs(self.targetpath, self.log,
                                     self.buildenv.xml, clean=False)
        else:
            self.targetfs = None

        # dont create sysroot instance, it should be build from scratch
        # each time, because the pkglist including the -dev packages is
        # tracked nowhere.
        self.sysrootenv = None
        self.log.do('rm -rf %s' % self.sysrootpath)

    def build_chroottarball(self):
        self.log.do("tar cJf %s/chroot.tar.xz \
                --exclude=./tmp/*  --exclude=./dev/* \
                --exclude=./run/*  --exclude=./sys/* \
                --exclude=./proc/* --exclude=./var/cache/* \
                -C %s ." % (self.builddir, self.chrootpath))

    def get_sysroot_paths(self):
        triplet = self.xml.defs["triplet"]

        paths = [
            './usr/include',
            './usr/include/' + triplet,
            './etc/ld.so.conf*',
            './opt/*/lib/*.so',
            './opt/*lib/*.so.*',
            './opt/*/include/',
            './opt/*/lib/' + triplet,
            './opt/*/include/' + triplet,
            './lib/*.so',
            './lib/*.so.*',
            './lib/' + triplet,
            './usr/lib/*.so',
            './usr/lib/*.so',
            './usr/lib/*.so.*',
            './usr/lib/' + triplet]

        return paths

    def build_sysroot(self):

        self.log.do('rm -rf %s; mkdir "%s"' % (self.sysrootpath,
                                               self.sysrootpath))

        self.sysrootenv = BuildEnv(self.xml,
                                   self.log,
                                   self.sysrootpath,
                                   clean=True)
        # Import keyring
        self.sysrootenv.import_keys()
        self.log.printo("Keys imported")

        self.install_packages(self.sysrootenv, buildenv=False)

        # ignore packages from debootstrap
        tpkgs = self.xml.get_target_packages()
        bspkgs = self.xml.node("debootstrappkgs")
        ignore_pkgs = [p.et.text for p in bspkgs if p.et.text not in tpkgs]
        ignore_dev_pkgs = []
        if self.xml.has('target/pkg-blacklist/sysroot'):
            ignore_dev_pkgs = [p.et.text for p in self.xml.node(
                "target/pkg-blacklist/sysroot")]

        with self.sysrootenv:
            try:
                self.get_rpcaptcache(env=self.sysrootenv).update()
            except Exception as e:
                raise AptCacheUpdateError(e)

            try:
                self.get_rpcaptcache(
                        env=self.sysrootenv).mark_install_devpkgs(
                                set(ignore_pkgs), set(ignore_dev_pkgs))
            except SystemError as e:
                self.log.printo("mark install devpkgs failed: %s" % str(e))
            try:
                self.get_rpcaptcache(env=self.sysrootenv).commit()
            except SystemError as e:
                self.log.printo("commiting changes failed: %s" % str(e))
                raise AptCacheCommitError(str(e))

        try:
            self.sysrootenv.rfs.dump_elbeversion(self.xml)
        except IOError:
            self.log.printo("dump elbeversion into sysroot failed")

        sysrootfilelist = os.path.join(self.builddir, "sysroot-filelist")

        with self.sysrootenv.rfs:
            self.log.do("chroot %s /usr/bin/symlinks -cr /usr/lib" %
                        self.sysrootpath)

        paths = self.get_sysroot_paths()

        self.log.do("rm %s" % sysrootfilelist, allow_fail=True)
        os.chdir(self.sysrootpath)
        for p in paths:
            self.log.do('find -path "%s" >> %s' % (p, sysrootfilelist))

        self.log.do("tar cfJ %s/sysroot.tar.xz -C %s -T %s" %
                    (self.builddir, self.sysrootpath, sysrootfilelist))

    def build_sdk(self):
        triplet = self.xml.defs["triplet"]

        try:
            crosstoolchainpkg = "g++-%s" % self.xml.defs["sdkarch"]
        except KeyError:
            raise UnsupportedSDKException(triplet)

        # build target sysroot including libs and headers for the target
        self.build_sysroot()
        sdktargetpath = os.path.join(self.sdkpath, "sysroots", "target")
        self.log.do("mkdir -p %s" % sdktargetpath)
        self.log.do("tar xJf %s/sysroot.tar.xz -C %s" % (self.builddir,
                                                         sdktargetpath))
        # build host sysroot including cross compiler
        hostsysrootpath = os.path.join(self.sdkpath, 'sysroots', 'host')
        self.log.do('mkdir -p "%s"' % hostsysrootpath)
        extract_pkg(self.xml.prj,
                    hostsysrootpath,
                    self.xml.defs,
                    crosstoolchainpkg,
                    'amd64',
                    self.log,
                    True)
        extract_pkg(self.xml.prj,
                    hostsysrootpath,
                    self.xml.defs,
                    'gdb-multiarch',
                    'amd64',
                    self.log,
                    True)

        n = gen_sdk_scripts(triplet,
                            self.name,
                            self.xml.text("project/version"),
                            self.builddir,
                            self.sdkpath)

        # create sdk tar and append it to setup script
        self.log.do("cd %s; tar cJf ../sdk.txz ." % self.sdkpath)
        self.log.do("cd %s; rm -rf sdk" % self.builddir)
        self.log.do("cd %s; cat sdk.txz >> %s" % (self.builddir, n))
        self.log.do("cd %s; chmod +x %s" % (self.builddir, n))
        self.log.do("cd %s; rm sdk.txz" % self.builddir)

    def pbuild(self, p):
        self.pdebuild_init()
        src_path = os.path.join(self.builddir, "pdebuilder", "current")

        src_uri = p.text('.').replace("LOCALMACHINE", "10.0.2.2").strip()
        self.log.printo("retrieve pbuild sources: %s" % src_uri)
        if p.tag == 'git':
            self.log.do("git clone %s %s" % (src_uri, src_path))
            try:
                self.log.do(
                    "cd %s; git reset --hard %s" %
                    (src_path, p.et.attrib['revision']))
            except IndexError:
                pass
        elif p.tag == 'svn':
            self.log.do("svn co --non-interactive %s %s" % (src_uri, src_path))
        else:
            self.log.printo("unknown pbuild source vcs: %s" % p.tag)

        # pdebuild_build(-1) means use all cpus
        self.pdebuild_build(cpuset=-1, profile="")

    def build_cdroms(self, build_bin=True,
                     build_sources=False, cdrom_size=None):
        self.repo_images = []

        elog = ASCIIDocLog(self.validationpath, True)

        env = None
        sysrootstr = ""
        if os.path.exists(self.sysrootpath):
            sysrootstr = "(including sysroot packages)"
            env = BuildEnv(self.xml, self.log, self.sysrootpath,
                           build_sources=build_sources, clean=False)
        else:
            env = BuildEnv(self.xml, self.log, self.chrootpath,
                           build_sources=build_sources, clean=False)

        # ensure the /etc/apt/sources.list is created according to
        # buil_sources, # build_bin flag, ensure to reopen it with
        # the new 'sources.list'
        with env:
            env.seed_etc()

        self.drop_rpcaptcache(env=env)

        with env:
            init_codename = self.xml.get_initvm_codename()

            if build_bin:
                elog.h1("Binary CD %s" % sysrootstr)

                self.repo_images += mk_binary_cdrom(env.rfs,
                                                    self.arch,
                                                    self.codename,
                                                    init_codename,
                                                    self.xml,
                                                    self.builddir,
                                                    self.log,
                                                    cdrom_size=cdrom_size)
            if build_sources:
                elog.h1("Source CD %s" % sysrootstr)
                try:
                    self.repo_images += mk_source_cdrom(env.rfs,
                                                        self.arch,
                                                        self.codename,
                                                        init_codename,
                                                        self.builddir,
                                                        self.log,
                                                        cdrom_size=cdrom_size,
                                                        xml=self.xml)
                except SystemError as e:
                    # e.g. no deb-src urls specified
                    elog.printo(str(e))

    def build(self, build_bin=False, build_sources=False, cdrom_size=None,
              skip_pkglist=False, skip_pbuild=False):

        # pylint: disable=too-many-arguments
        # pylint: disable=too-many-locals
        # pylint: disable=too-many-statements
        # pylint: disable=too-many-branches

        # Write the log header
        self.write_log_header()

        # Validate Apt Sources
        if build_sources:
            m = ValidationMode.CHECK_ALL
        else:
            m = ValidationMode.CHECK_BINARIES

        self.xml.validate_apt_sources(m, self.arch)

        if self.xml.has('target/pbuilder') and not skip_pbuild:
            if not os.path.exists(os.path.join(self.builddir, "pbuilder")):
                self.create_pbuilder()
            for p in self.xml.node('target/pbuilder'):
                self.pbuild(p)
                # the package might be needed by a following pbuild, so update
                # the project repo that it can be installed in as
                # build-dependency
                self.repo.finalize()

        # To avoid update cache errors, the project repo needs to have
        # Release and Packages files, even if it's empty. So don't do this
        # in the if case above!
        self.repo.finalize()

        # Create the build environment, if it does not a valid one
        # self.buildenv might be set when we come here.
        # However, if its not a full_buildenv, we specify clean here,
        # so it gets rebuilt properly.
        if not self.has_full_buildenv():
            self.log.do('mkdir -p "%s"' % self.chrootpath)
            self.buildenv = BuildEnv(self.xml, self.log, self.chrootpath,
                                     build_sources=build_sources, clean=True)
            skip_pkglist = False

        # Import keyring
        self.buildenv.import_keys()
        self.log.printo("Keys imported")

        # Install packages
        if not skip_pkglist:
            self.install_packages(self.buildenv)

        try:
            self.buildenv.rfs.dump_elbeversion(self.xml)
        except IOError:
            self.log.printo("dump elbeversion failed")

        # Extract target FS. We always create a new instance here with
        # clean=true, because we want a pristine directory.
        self.targetfs = TargetFs(self.targetpath, self.log,
                                 self.buildenv.xml, clean=True)
        os.chdir(self.buildenv.rfs.fname(''))
        extract_target(self.buildenv.rfs, self.xml, self.targetfs,
                       self.log, self.get_rpcaptcache())

        # The validation file is created using check_full_pkgs() and
        # elbe_report(), both opening the file in append mode. So if an
        # old validation file already exists, it must be deleted first.
        if os.path.isfile(self.validationpath):
            os.unlink(self.validationpath)

        # Package validation and package list
        if not skip_pkglist:
            pkgs = self.xml.xml.node("/target/pkg-list")
            if self.xml.has("fullpkgs"):
                check_full_pkgs(pkgs, self.xml.xml.node("/fullpkgs"),
                                self.validationpath, self.get_rpcaptcache())
            else:
                check_full_pkgs(pkgs, None, self.validationpath,
                                self.get_rpcaptcache())
            dump_fullpkgs(self.xml, self.buildenv.rfs, self.get_rpcaptcache())

            self.xml.dump_elbe_version()

        self.targetfs.write_fstab(self.xml)

        # Dump ELBE version
        try:
            self.targetfs.dump_elbeversion(self.xml)
        except MemoryError:
            self.log.printo("dump elbeversion failed")

        # install packages for buildenv
        if not skip_pkglist:
            self.install_packages(self.buildenv, buildenv=True)

        # Write source.xml
        try:
            sourcexmlpath = os.path.join(self.builddir, "source.xml")
            self.xml.xml.write(sourcexmlpath)
        except MemoryError:
            self.log.printo("write source.xml failed (archive to huge?)")

        # Elbe report
        reportpath = os.path.join(self.builddir, "elbe-report.txt")
        elbe_report(self.xml, self.buildenv, self.get_rpcaptcache(),
                    reportpath, self.validationpath, self.targetfs)

        # the current license code raises an exception that interrupts the hole
        # build if a licence can't be converted to utf-8. Exception handling
        # can be removed as soon as the licence code is more stable
        lic_err = False
        try:
            f = io.open(
                os.path.join(
                    self.builddir,
                    "licence.txt"),
                "w+",
                encoding='utf-8')
            self.buildenv.rfs.write_licenses(
                f, self.log, os.path.join(
                    self.builddir, "licence.xml"))
        except Exception:
            self.log.printo("error during generating licence.txt/xml")
            self.log.printo(sys.exc_info()[0])
            lic_err = True
        finally:
            f.close()
        if lic_err:
            os.remove(os.path.join(self.builddir, "licence.txt"))
            os.remove(os.path.join(self.builddir, "licence.xml"))

        # Use some handwaving to determine grub version
        # jessie and wheezy grubs are 2.0 but differ in behaviour
        #
        # We might also want support for legacy grub
        if (self.get_rpcaptcache().is_installed('grub-pc') and
                self.get_rpcaptcache().is_installed('grub-efi-amd64-bin')):
            grub_version = 202
            grub_fw_type = "hybrid"
        elif self.get_rpcaptcache().is_installed('grub-pc'):
            if self.codename == "wheezy":
                grub_version = 199
            else:
                grub_version = 202
            grub_fw_type = "bios"
        elif self.get_rpcaptcache().is_installed('grub-efi-amd64'):
            grub_version = 202
            grub_fw_type = "efi"
        elif self.get_rpcaptcache().is_installed('grub-legacy'):
            self.log.printo("package grub-legacy is installed, "
                            "this is obsolete, skipping grub")
            grub_version = 0
            grub_fw_type = ""
        else:
            self.log.printo("package grub-pc is not installed, skipping grub")
            # version 0 == skip_grub
            grub_version = 0
            grub_fw_type = ""
        self.targetfs.part_target(self.builddir, grub_version, grub_fw_type)

        self.build_cdroms(build_bin, build_sources, cdrom_size)

        if self.postbuild_file:
            self.log.h2("postbuild script:")
            self.log.do(self.postbuild_file + ' "%s %s %s"' % (
                self.builddir,
                self.xml.text("project/version"),
                self.xml.text("project/name")),
                allow_fail=True)

        do_prj_finetuning(self.xml,
                          self.log,
                          self.buildenv,
                          self.targetfs,
                          self.builddir)

        self.targetfs.pack_images(self.builddir)

        os.system('cat "%s"' % self.validationpath)

    def pdebuild_init(self):
        # Remove pdebuilder directory, containing last build results
        self.log.do('rm -rf "%s"' % os.path.join(self.builddir,
                                                 "pdebuilder"))

        # Remove pbuilder/result directory
        self.log.do('rm -rf "%s"' % os.path.join(self.builddir,
                                                 "pbuilder", "result"))

        # Recreate the directories removed
        self.log.do('mkdir -p "%s"' % os.path.join(self.builddir,
                                                   "pbuilder", "result"))

    def pdebuild(self, cpuset, profile):
        self.pdebuild_init()

        pbdir = os.path.join(self.builddir, "pdebuilder", "current")
        self.log.do('mkdir -p "%s"' % os.path.join(pbdir))

        try:
            for orig_fname in self.orig_files:
                ofname = os.path.join(self.builddir, orig_fname)
                self.log.do('mv "%s" "%s"' % (ofname,
                                              os.path.join(self.builddir,
                                                           "pdebuilder")))
        finally:
            self.orig_fname = None
            self.orig_files = []

        # Untar current_pdebuild.tar.gz into pdebuilder/current
        self.log.do(
            'tar xfz "%s" -C "%s"' %
            (os.path.join(
                self.builddir,
                "current_pdebuild.tar.gz"),
                pbdir))

        self.pdebuild_build(cpuset, profile)
        self.repo.finalize()

    def pdebuild_build(self, cpuset, profile):
        # check whether we have to use taskset to run pdebuild
        # this might be useful, when things like java dont
        # work with multithreading
        #
        if cpuset != -1:
            cpuset_cmd = 'taskset %d ' % cpuset
        else:
            # cpuset == -1 means empty cpuset_cmd
            cpuset_cmd = ''

        try:
            self.log.do('cd "%s"; %s pdebuild --debbuildopts "-j%s -sa" '
                        '--configfile "%s" '
                        '--use-pdebuild-internal --buildresult "%s"' % (
                            os.path.join(self.builddir,
                                         "pdebuilder",
                                         "current"),
                            cpuset_cmd,
                            cfg['pbuilder_jobs'],
                            os.path.join(self.builddir, "pbuilderrc"),
                            os.path.join(self.builddir, "pbuilder", "result")),
                        env_add={'DEB_BUILD_PROFILES': profile})

            self.repo.remove(os.path.join(self.builddir,
                                          "pdebuilder",
                                          "current",
                                          "debian",
                                          "control"))

            self.repo.include(os.path.join(self.builddir,
                                           "pbuilder", "result", "*.changes"))
        except CommandError:
            self.log.printo('')
            self.log.printo('Package fails to build.')
            self.log.printo('Please make sure, that the submitted package '
                            'builds in pbuilder')

    def update_pbuilder(self):
        self.log.do(
            'pbuilder --update --configfile "%s" --aptconfdir "%s"' %
            (os.path.join(
                self.builddir, "pbuilderrc"), os.path.join(
                self.builddir, "aptconfdir")))

    def create_pbuilder(self):
        # Remove old pbuilder directory, if it exists
        self.log.do('rm -rf "%s"' % os.path.join(self.builddir, "pbuilder"))

        # make hooks.d and pbuilder directory
        self.log.do(
            'mkdir -p "%s"' %
            os.path.join(
                self.builddir,
                "pbuilder",
                "hooks.d"))
        self.log.do(
            'mkdir -p "%s"' %
            os.path.join(
                self.builddir,
                "aptconfdir",
                "apt.conf.d"))

        # write config files
        pbuilder_write_config(self.builddir, self.xml, self.log)
        pbuilder_write_apt_conf(self.builddir, self.xml)
        pbuilder_write_repo_hook(self.builddir, self.xml)
        self.log.do(
            'chmod 755 "%s"' %
            os.path.join(
                self.builddir,
                "pbuilder",
                "hooks.d",
                "D10elbe_apt_sources"))

        # Run pbuilder --create
        self.log.do('pbuilder --create --configfile "%s" --aptconfdir "%s" '
                    '--extrapackages "git gnupg"' % (
                        os.path.join(self.builddir, "pbuilderrc"),
                        os.path.join(self.builddir, "aptconfdir")))

    def sync_xml_to_disk(self):
        try:
            sourcexmlpath = os.path.join(self.builddir, "source.xml")
            self.xml.xml.write(sourcexmlpath)
        except MemoryError:
            self.log.printo("write source.xml failed (archive to huge?)")

    def get_rpcaptcache(self, env=None):
        if not env:
            env = self.buildenv
        if env.rpcaptcache is None:
            env.rpcaptcache = get_rpcaptcache(
                env.rfs,
                self.log.fp.name,
                self.arch,
                self.rpcaptcache_notifier,
                self.xml.prj.has('norecommend'),
                self.xml.prj.has('noauth'))
        return env.rpcaptcache

    def drop_rpcaptcache(self, env=None):
        if not env:
            env = self.buildenv
        env.rpcaptcache = None

    def has_full_buildenv(self):
        if os.path.exists(self.chrootpath):
            elbeversionpath = os.path.join(self.chrootpath,
                                           "etc", "elbe_version")
            if os.path.isfile(elbeversionpath):
                return True

            self.log.printo("%s exists, but it does not have "
                            "an etc/elbe_version file." % self.chrootpath)
            # Apparently we do not have a functional build environment
            return False

        return False

    def set_xml(self, xmlpath):
        # Use supplied XML file, if given, otherwise change to source.xml
        if not xmlpath:
            xmlpath = os.path.join(self.builddir, "source.xml")

        newxml = ElbeXML(xmlpath, buildtype=self.override_buildtype,
                         skip_validate=self.skip_validate,
                         url_validation=self.url_validation)

        # New XML file has to have the same architecture
        oldarch = self.xml.text("project/arch", key="arch")
        newarch = newxml.text("project/arch", key="arch")
        if newarch != oldarch:
            raise IncompatibleArchitectureException(oldarch, newarch)

        # Throw away old APT cache, targetfs and buildenv
        self.targetfs = None
        self.buildenv = None

        # dont create sysroot instance, it should be build from scratch
        # each time, because the pkglist including the -dev packages is
        # tracked nowhere.
        self.sysrootenv = None
        self.log.do('rm -rf %s' % self.sysrootpath)

        self.xml = newxml

        # Create a new BuildEnv instance, if we have a build directory
        if self.has_full_buildenv():
            self.buildenv = BuildEnv(
                self.xml, self.log, self.chrootpath, clean=False)

        # Create TargetFs instance, if the target directory exists.
        # We use the old content of the directory if no rebuild is done, so
        # don't clean it (yet).
        if os.path.exists(self.targetpath):
            self.targetfs = TargetFs(self.targetpath, self.log,
                                     self.xml, clean=False)
        else:
            self.targetfs = None

    def write_log_header(self):
        if self.name:
            self.log.h1("ELBE Report for Project " + self.name)
        else:
            self.log.h1("ELBE Report")
        self.log.printo("report timestamp: " +
                        datetime.datetime.now().strftime("%Y%m%d-%H%M%S"))

    def install_packages(self, target, buildenv=False):

        # pylint: disable=too-many-statements
        # pylint: disable=too-many-branches

        with target:
            # First update the apt cache
            try:
                self.get_rpcaptcache(env=target).update()
            except Exception as e:
                raise AptCacheUpdateError(e)

            # Then dump the debootstrap packages
            if target.fresh_debootstrap:
                if target.need_dumpdebootstrap:
                    dump_debootstrappkgs(self.xml,
                                         self.get_rpcaptcache(env=target))
                    dump_initvmpkgs(self.xml)
                target.need_dumpdebootstrap = False
                source = self.xml
                try:
                    initxml = ElbeXML(
                        "/var/cache/elbe/source.xml",
                        skip_validate=self.skip_validate,
                        url_validation=ValidationMode.NO_CHECK)
                    self.xml.get_initvmnode_from(initxml)
                except ValidationError as e:
                    self.log.printo(
                        "/var/cache/elbe/source.xml validation failed")
                    self.log.printo(str(e))
                    self.log.printo("will not copy initvm node")
                except IOError:
                    self.log.printo("/var/cache/elbe/source.xml not available")
                    self.log.printo("can not copy initvm node")
                except NoInitvmNode:
                    self.log.printo("/var/cache/elbe/source.xml is available")
                    self.log.printo("But it does not contain an initvm node")
            else:
                sourcepath = os.path.join(self.builddir, "source.xml")
                source = ElbeXML(sourcepath,
                                 buildtype=self.override_buildtype,
                                 skip_validate=self.skip_validate,
                                 url_validation=self.url_validation)

                self.xml.get_debootstrappkgs_from(source)
                try:
                    self.xml.get_initvmnode_from(source)
                except NoInitvmNode:
                    self.log.printo("source.xml is available")
                    self.log.printo("But it does not contain an initvm node")

            # Seed /etc, we need /etc/hosts for hostname -f to work correctly
            if not buildenv:
                target.seed_etc()

            # remove all non-essential packages to ensure that on a incremental
            # build packages can be removed
            debootstrap_pkgs = []
            for p in self.xml.node("debootstrappkgs"):
                debootstrap_pkgs.append(p.et.text)

            pkgs = target.xml.get_target_packages() + debootstrap_pkgs

            if buildenv:
                pkgs = pkgs + target.xml.get_buildenv_packages()

            # Now install requested packages
            for p in pkgs:
                try:
                    self.get_rpcaptcache(env=target).mark_install(p, None)
                except KeyError:
                    self.log.printo("No Package " + p)
                except SystemError as e:
                    self.log.printo("Error: Unable to correct problems in package %s (%s)" % (p, str(e)))

            # temporary disabled because of
            # https://bugs.debian.org/cgi-bin/bugreport.cgi?bug=776057
            # the functions cleans up to much
            # self.get_rpcaptcache().cleanup(debootstrap_pkgs + pkgs)

            try:
                self.get_rpcaptcache(env=target).commit()
            except SystemError as e:
                self.log.printo("commiting changes failed: %s" % str(e))
                raise AptCacheCommitError(str(e))
