# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2014-2018 Linutronix GmbH


import datetime
import glob
import io
import logging
import os
import shutil
import subprocess
import sys
import tarfile

from debian.changelog import Changelog

from elbepack.aptpkgutils import XMLPackage
from elbepack.archivedir import archive_tmpfile
from elbepack.cdroms import mk_binary_cdrom, mk_source_cdrom
from elbepack.dump import (
    check_full_pkgs,
    dump_debootstrappkgs,
    dump_fullpkgs,
    dump_initvmpkgs,
    elbe_report,
)
from elbepack.efilesystem import TargetFs, extract_target
from elbepack.elbexml import ElbeXML, NoInitvmNode, ValidationError, ValidationMode
from elbepack.filesystem import size_to_int
from elbepack.finetuning import do_prj_finetuning
from elbepack.log import validation
from elbepack.pbuilder import (
    pbuilder_get_debootstrap_key_path,
    pbuilder_write_apt_conf,
    pbuilder_write_config,
    pbuilder_write_cross_config,
    pbuilder_write_repo_hook,
)
from elbepack.repomanager import ProjectRepo
from elbepack.rfs import BuildEnv
from elbepack.rpcaptcache import get_rpcaptcache
from elbepack.shellhelper import chroot, do
from elbepack.templates import write_pack_template
from elbepack.version import elbe_version


_xz_env = {
    'XZ_OPT': '-T0 -M40%',
}


class IncompatibleArchitectureException(Exception):
    def __init__(self, oldarch, newarch):
        super().__init__(f'Cannot change architecture from {oldarch} to {newarch} in '
                         'existing project')


class AptCacheUpdateError(Exception):
    def __init__(self, e):
        super().__init__(f'Error Updating rpcaptcache: {e}')


class AptCacheCommitError(Exception):
    def __init__(self, msg=''):
        super().__init__(f'Error Committing rpcaptcache {msg}')


def test_gen_sdk_scripts():
    os.makedirs('/tmp/test/sdk')
    gen_sdk_scripts('armhf-linux-gnueabihf',
                    'ARM',
                    'testproject',
                    '08.15',
                    '/tmp/test',
                    '/tmp/test/sdk')


def gen_sdk_scripts(triplet,
                    elfcode,
                    prj_name,
                    prj_version,
                    builddir,
                    sdkpath):

    prj_name = prj_name.replace(' ', '_')
    prj_version = prj_version.replace(' ', '_')

    # generate the setup script
    sdkvalues = {'sdk_arch': 'x86_64',
                 'sdk_gcc_ver': '',
                 'sdk_path': f'/opt/elbe-sdk-{triplet}-{prj_name}-{prj_version}',
                 'sdk_ext_path': '~/elbe-sdk',
                 'real_multimach_target_sys': triplet,
                 'target_elfcode': elfcode,
                 'sdk_title': f'ELBE {prj_name}',
                 'sdk_version': prj_version}

    sdkname = f'setup-elbe-sdk-{triplet}-{prj_name}-{prj_version}.sh'
    write_pack_template(os.path.join(builddir, sdkname),
                        'toolchain-shar-extract.sh.mako',
                        sdkvalues)
    envname = f'environment-setup-elbe-{triplet}-{prj_name}-{prj_version}'
    write_pack_template(os.path.join(sdkpath, envname),
                        'environment-setup-elbe.mako',
                        sdkvalues)

    return sdkname


class ElbeProject:

    def __init__(
            self,
            builddir,
            xmlpath=None,
            name=None,
            override_buildtype=None,
            skip_validate=False,
            url_validation=ValidationMode.CHECK_ALL,
            postbuild_file=None,
            presh_file=None,
            postsh_file=None,
            savesh_file=None):

        self.builddir = os.path.abspath(str(builddir))
        self.chrootpath = os.path.join(self.builddir, 'chroot')
        self.targetpath = os.path.join(self.builddir, 'target')
        self.sysrootpath = os.path.join(self.builddir, 'sysroot')
        self.sdkpath = os.path.join(self.builddir, 'sdk')
        self.validationpath = os.path.join(self.builddir, 'validation.txt')

        self.name = name
        self.override_buildtype = override_buildtype
        self.skip_validate = skip_validate
        self.url_validation = url_validation
        self.postbuild_file = postbuild_file
        self.presh_file = presh_file
        self.postsh_file = postsh_file
        self.savesh_file = savesh_file

        # Apt-Cache will be created on demand by the get_rpcaptcache method
        self._rpcaptcache = None

        # Initialise Repo Images to Empty list.
        self.repo_images = []

        # Use supplied XML file, if given, otherwise use the source.xml
        # file of the project
        if xmlpath:
            self.xml = ElbeXML(
                xmlpath,
                buildtype=override_buildtype,
                skip_validate=skip_validate,
                url_validation=url_validation)
        else:
            sourcexmlpath = os.path.join(self.builddir, 'source.xml')
            self.xml = ElbeXML(
                sourcexmlpath,
                buildtype=override_buildtype,
                skip_validate=skip_validate,
                url_validation=url_validation)

        self.arch = self.xml.text('project/arch', key='arch')
        self.codename = self.xml.text('project/suite')

        if not self.name:
            self.name = self.xml.text('project/name')

        self.repo = ProjectRepo(self.arch, self.codename,
                                os.path.join(self.builddir, 'repo'))

        # Create BuildEnv instance, if the chroot directory exists and
        # has an etc/elbe_version
        if os.path.exists(self.chrootpath):
            self.buildenv = BuildEnv(self.xml,
                                     self.chrootpath,
                                     clean=False)
        else:
            self.buildenv = None

        # Create TargetFs instance, if the target directory exists
        if os.path.exists(self.targetpath) and self.buildenv:
            self.targetfs = TargetFs(self.targetpath, self.buildenv.xml,
                                     clean=False)
        else:
            self.targetfs = None

        # don't create sysroot instance, it should be built from scratch
        # each time, because the pkglist including the -dev packages is
        # tracked nowhere.
        self.sysrootenv = None
        do(['rm', '-rf', self.sysrootpath])

        # same for host_sysroot instance recreate it in any case
        self.host_sysrootenv = None

    def build_chroottarball(self):
        do(['tar', 'cJf', self.builddir + '/chroot.tar.xz',
            '--exclude=./tmp/*', '--exclude=./dev/*',
            '--exclude=./run/*', '--exclude=./sys/*',
            '--exclude=./proc/*', '--exclude=./var/cache/*',
            '-C', self.chrootpath, '.'],
            env_add=_xz_env)

    def get_sysroot_paths(self):
        triplet = self.xml.defs['triplet']

        return [
            './usr/include',
            './usr/include/' + triplet,
            './usr/bin/gdbserver',
            './usr/sbin/ldconfig',
            './usr/share/pkgconfig',
            './usr/share/cmake',
            './etc/ld.so.conf*',
            './opt/*/lib/*.a',
            './opt/*/lib/*.so',
            './opt/*lib/*.so.*',
            './opt/*/include',
            './opt/*/lib/' + triplet,
            './opt/*/include/' + triplet,
            './lib/*.a',
            './lib/*.so',
            './lib/*.so.*',
            './lib/' + triplet,
            './usr/lib/debug/.build-id/*/*.debug',
            './usr/lib/*.a',
            './usr/lib/*.so',
            './usr/lib/*.so.*',
            './usr/lib/' + triplet,
            './usr/lib/pkgconfig',
            './usr/lib64/*.so.*',
        ]

    def build_sysroot(self):

        do(['rm', '-rf', self.sysrootpath])
        do(['mkdir', self.sysrootpath])

        self.sysrootenv = BuildEnv(self.xml,
                                   self.sysrootpath,
                                   clean=True)
        # Import keyring
        self.sysrootenv.import_keys()
        logging.info('Keys imported')

        self.xml.add_target_package('libc-bin')
        self.xml.add_target_package('libc6-dbg')
        self.xml.add_target_package('gdbserver')

        self.install_packages(self.sysrootenv, buildenv=False)

        # ignore packages from debootstrap
        tpkgs = self.xml.get_target_packages()
        bspkgs = self.xml.node('debootstrappkgs')
        ignore_pkgs = [p.et.text for p in bspkgs if p.et.text not in tpkgs]
        ignore_dev_pkgs = []
        if self.xml.has('target/pkg-blacklist/sysroot'):
            ignore_dev_pkgs = [p.et.text for p in self.xml.node(
                'target/pkg-blacklist/sysroot')]

        with self.sysrootenv:
            try:
                cache = self.get_rpcaptcache(env=self.sysrootenv)
                cache.update()
            except Exception as e:
                raise AptCacheUpdateError(e)

            try:
                cache.mark_install_devpkgs(set(ignore_pkgs),
                                           set(ignore_dev_pkgs))
            except SystemError:
                logging.exception('Mark install devpkgs failed')
            try:
                cache.commit()
            except SystemError as e:
                logging.exception('Commiting changes failed')
                raise AptCacheCommitError(str(e))

            self.gen_licenses('sysroot-target', self.sysrootenv,
                              [p.name for p in cache.get_installed_pkgs()])

        try:
            self.sysrootenv.rfs.dump_elbeversion(self.xml)
        except IOError:
            logging.exception('Dump elbeversion into sysroot failed')

        sysrootfilelist = os.path.join(self.builddir, 'sysroot-filelist')

        with self.sysrootenv.rfs:
            chroot(self.sysrootpath, ['/usr/bin/symlinks', '-cr', '/usr/lib'])
            chroot(self.sysrootpath, ['/usr/bin/symlinks', '-cr', '/usr/lib64'])

        paths = self.get_sysroot_paths()

        do(['rm', sysrootfilelist], check=False)
        os.chdir(self.sysrootpath)
        for p in paths:
            do(f'find -path "{p}" >> {sysrootfilelist}')
        with open(sysrootfilelist, 'a') as filelist_fd:
            # include /lib if it is a symlink (buster and later)
            if os.path.islink(self.sysrootpath + '/lib'):
                filelist_fd.write('./lib\n')

            if os.path.islink(self.sysrootpath + '/lib64'):
                filelist_fd.write('./lib64\n')

            if os.path.islink(self.sysrootpath + '/sbin'):
                filelist_fd.write('./sbin\n')

        do(['tar', 'cfJ', os.path.join(self.builddir, 'sysroot.tar.xz'),
            '-C', self.sysrootpath, '-T', sysrootfilelist],
           env_add=_xz_env)

    def build_host_sysroot(self, pkgs, hostsysrootpath):
        do(['rm', '-rf', hostsysrootpath])
        do(['mkdir', hostsysrootpath])

        self.host_sysrootenv = BuildEnv(self.xml,
                                        hostsysrootpath,
                                        clean=True,
                                        arch='amd64',
                                        hostsysroot=True)
        # Import keyring
        self.host_sysrootenv.import_keys()
        logging.info('Keys imported')

        with self.host_sysrootenv:

            try:
                cache = self.get_rpcaptcache(env=self.host_sysrootenv,
                                             norecommend=True)
                cache.update()
            except Exception as e:
                raise AptCacheUpdateError(e)

            for p in pkgs:
                try:
                    cache.mark_install(p, None)
                except KeyError:
                    logging.exception('No Package %s', p)
                except SystemError:
                    logging.exception('Unable to correct problems in '
                                      'package %s',
                                      p)

            try:
                cache.commit()
            except SystemError as e:
                logging.exception('Commiting changes failed')
                raise AptCacheCommitError(str(e))

            self.gen_licenses('sysroot-host', self.host_sysrootenv,
                              [p.name for p in cache.get_installed_pkgs()])

        # This is just a sysroot, some directories
        # need to be removed.
        #
        # This can move into finetuning in the
        # second implementation step.
        self.host_sysrootenv.rfs.rmtree('/boot')
        self.host_sysrootenv.rfs.rmtree('/dev')
        self.host_sysrootenv.rfs.rmtree('/etc')
        self.host_sysrootenv.rfs.rmtree('/home')
        self.host_sysrootenv.rfs.rmtree('/media')
        self.host_sysrootenv.rfs.rmtree('/mnt')
        self.host_sysrootenv.rfs.rmtree('/proc')
        self.host_sysrootenv.rfs.rmtree('/root')
        self.host_sysrootenv.rfs.rmtree('/run')
        self.host_sysrootenv.rfs.rmtree('/sys')
        self.host_sysrootenv.rfs.rmtree('/tmp')
        self.host_sysrootenv.rfs.rmtree('/var')

    def build_sdk(self):
        triplet = self.xml.defs['triplet']
        elfcode = self.xml.defs['elfcode']

        host_pkglist = []
        if self.xml.tgt.has('hostsdk-pkg-list'):
            for p in self.xml.tgt.node('hostsdk-pkg-list'):
                if p.tag == 'pkg':
                    host_pkglist.append(p.et.text.strip())
        else:
            if triplet == 'x86_64-linux-gnu':
                compiler_package = 'g++'
            else:
                compiler_package = f'g++-{triplet}'

            host_pkglist.append(compiler_package)
            host_pkglist.append('gdb-multiarch')

        # build target sysroot including libs and headers for the target
        self.build_sysroot()
        sdktargetpath = os.path.join(self.sdkpath, 'sysroots', 'target')
        do(['mkdir', '-p', sdktargetpath])
        do(['tar', 'xJf', os.path.join(self.builddir, 'sysroot.tar.xz'), '-C', sdktargetpath],
           env_add=_xz_env)
        # build host sysroot including cross compiler
        hostsysrootpath = os.path.join(self.sdkpath, 'sysroots', 'host')

        self.build_host_sysroot(host_pkglist, hostsysrootpath)

        n = gen_sdk_scripts(triplet,
                            elfcode,
                            self.name,
                            self.xml.text('project/version'),
                            self.builddir,
                            self.sdkpath)

        # create sdk tar and append it to setup script
        do(['tar', 'cJf', '../sdk.txz', '.'], cwd=self.sdkpath, env_add=_xz_env)
        do(['rm', '-rf', 'sdk'], cwd=self.builddir)
        do(f'cat sdk.txz >> {n}', cwd=self.builddir)
        do(['chmod', '+x', n], cwd=self.builddir)
        do(['rm', 'sdk.txz'], cwd=self.builddir)

    def pbuild(self, p):
        self.pdebuild_init()
        os.mkdir(os.path.join(self.builddir, 'pdebuilder'))
        src_path = os.path.join(self.builddir, 'pdebuilder', 'current')

        if p.tag != 'archive':
            src_uri = p.text('.').replace('LOCALMACHINE', '10.0.2.2').strip()
            logging.info('Retrieve pbuild sources: %s',  src_uri)

        if p.tag == 'git':
            do(['git', 'clone', src_uri, src_path])
            revision = p.et.get('revision')
            if revision is not None:
                do(['git', 'reset', '--hard', revision], cwd=src_path)
        elif p.tag == 'svn':
            do(['svn', 'co', '--non-interactive', src_uri, src_path])
        elif p.tag == 'src-pkg':
            apt_args = ['--yes', '-q', '--download-only']
            if self.xml.prj.has('noauth'):
                apt_args.append('--allow-unauthenticated')

            with self.buildenv:
                chroot(self.chrootpath, ['/usr/bin/apt-get', 'update'])
                chroot(self.chrootpath, ['/usr/bin/apt-get', 'source', *apt_args, src_uri])

            do(f'dpkg-source -x {self.chrootpath}/*.dsc "{src_path}"; rm {self.chrootpath}/*.dsc')
        elif p.tag == 'archive':
            logging.info('Retrieve pbuild sources from archive')
            with archive_tmpfile(p.text('.')) as archive_file:
                with tarfile.open(archive_file.name) as archive:
                    archive.extractall(path=src_path)
        else:
            logging.info('Unknown pbuild source: %s', p.tag)

        self.pdebuild_build(profile='', cross=False)

    def build_cdroms(self, build_bin=True,
                     build_sources=False, cdrom_size=None,
                     tgt_pkg_lst=None):

        self.repo_images = []

        env = None
        sysrootstr = ''
        if os.path.exists(self.sysrootpath):
            sysrootstr = ' (including sysroot packages)'
            env = BuildEnv(self.xml, self.sysrootpath,
                           build_sources=build_sources, clean=False)
        else:
            env = BuildEnv(self.xml, self.chrootpath,
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
                validation.info('Binary CD' + sysrootstr)

                self.repo_images += mk_binary_cdrom(env.rfs,
                                                    self.arch,
                                                    self.codename,
                                                    init_codename,
                                                    self.xml,
                                                    self.builddir)
            if build_sources:
                if not cdrom_size and self.xml.has('src-cdrom/size'):
                    cdrom_size = size_to_int(self.xml.text('src-cdrom/size'))

                validation.info('Source CD' + sysrootstr)

                # Target component
                cache = self.get_rpcaptcache(env=self.buildenv)
                tgt_lst = cache.get_corresponding_source_packages(pkg_lst=tgt_pkg_lst)
                components = {'target': (self.buildenv.rfs, cache, tgt_lst)}

                # Main component
                main_lst = []
                if self.xml is not None:
                    tmp_lst = []
                    for pkg_node in self.xml.node('debootstrappkgs'):
                        pkg = XMLPackage(pkg_node)
                        tmp_lst.append(pkg.name)
                    main_lst = cache.get_corresponding_source_packages(pkg_lst=tmp_lst)
                components['main'] = (env.rfs, cache, main_lst)

                # Added component
                other_components = [(env, 'added')]

                # Let's build a list of (build_env, name) for the
                # other RFS if they exist
                host_sysroot_path = os.path.join(self.sdkpath, 'sysroots', 'host')
                for path, name in [(self.chrootpath, 'chroot'),
                                   (host_sysroot_path, 'sysroot-host')]:
                    if os.path.exists(path) and env.path != path:
                        tmp_env = BuildEnv(self.xml, path)
                        with tmp_env:
                            tmp_env.seed_etc()
                        other_components.append((tmp_env, name))

                # Now let's generate the correct (rfs, cache, pkg_lst)
                # components using the full installed packages
                for build_env, name in other_components:
                    cache = self.get_rpcaptcache(env=build_env)
                    src_lst = cache.get_corresponding_source_packages()
                    components[name] = (build_env.rfs, cache, src_lst)

                try:
                    # Using kwargs here allows us to avoid making
                    # special case for when self.xml is None
                    kwargs = {
                        'cdrom_size': cdrom_size,
                        'xml': self.xml
                        }

                    if self.xml is not None:
                        kwargs['mirror'] = self.xml.get_primary_mirror(env.rfs.fname('cdrom'))

                    for iso in mk_source_cdrom(components,
                                               self.codename,
                                               init_codename,
                                               self.builddir,
                                               **kwargs):
                        self.repo_images += iso
                except SystemError as e:
                    # e.g. no deb-src urls specified
                    validation.error(str(e))

    def build(self, build_bin=False, build_sources=False, cdrom_size=None,
              skip_pkglist=False, skip_pbuild=False):

        # Write the log header
        self.write_log_header()

        # Validate Apt Sources
        if build_sources:
            m = ValidationMode.CHECK_ALL
        else:
            m = ValidationMode.CHECK_BINARIES

        self.xml.validate_apt_sources(m, self.arch)

        # Create the build environment, if it does not a valid one
        # self.buildenv might be set when we come here.
        # However, if its not a full_buildenv, we specify clean here,
        # so it gets rebuilt properly.
        if not self.has_full_buildenv():
            do(['mkdir', '-p', self.chrootpath])
            self.buildenv = BuildEnv(self.xml, self.chrootpath,
                                     build_sources=build_sources, clean=True)
            skip_pkglist = False

        # Import keyring
        self.buildenv.import_keys()
        logging.info('Keys imported')

        if self.xml.has('target/pbuilder') and not skip_pbuild:
            if not os.path.exists(os.path.join(self.builddir, 'pbuilder')):
                self.create_pbuilder(cross=False, noccache=False,
                                     ccachesize='10G')
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

        # Install packages
        if not skip_pkglist:
            self.install_packages(self.buildenv)

        try:
            self.buildenv.rfs.dump_elbeversion(self.xml)
        except IOError:
            logging.exception('Dump elbeversion failed')

        # Extract target FS. We always create a new instance here with
        # clean=true, because we want a pristine directory.
        self.targetfs = TargetFs(self.targetpath, self.buildenv.xml,
                                 clean=True)
        os.chdir(self.buildenv.rfs.fname(''))
        extract_target(self.buildenv.rfs, self.xml, self.targetfs,
                       self.get_rpcaptcache())

        # Package validation and package list
        if not skip_pkglist:
            pkgs = self.xml.xml.node('/target/pkg-list')
            if self.xml.has('fullpkgs'):
                check_full_pkgs(pkgs, self.xml.xml.node('/fullpkgs'),
                                self.get_rpcaptcache())
            else:
                check_full_pkgs(pkgs, None, self.get_rpcaptcache())
            dump_fullpkgs(self.xml, self.buildenv.rfs, self.get_rpcaptcache())

            self.xml.dump_elbe_version()

        self.targetfs.write_fstab(self.xml)

        # Dump ELBE version
        try:
            self.targetfs.dump_elbeversion(self.xml)
        except MemoryError:
            logging.exception('Dump elbeversion failed')

        # install packages for buildenv
        if not skip_pkglist:
            self.install_packages(self.buildenv, buildenv=True)

        # Write source.xml
        try:
            sourcexmlpath = os.path.join(self.builddir, 'source.xml')
            self.xml.xml.write(sourcexmlpath)
        except MemoryError:
            logging.exception('Write source.xml failed (archive to huge?)')

        # Elbe report
        cache = self.get_rpcaptcache()
        tgt_pkgs = elbe_report(self.xml, self.buildenv, cache, self.targetfs)

        # chroot' licenses
        self.gen_licenses('chroot', self.buildenv,
                          [p.name for p in cache.get_installed_pkgs()])

        self.gen_licenses('target', self.buildenv, tgt_pkgs)

        # Use some handwaving to determine grub version
        grub_arch = 'ia32' if self.arch == 'i386' else self.arch
        grub_fw_type = []
        grub_version = 0
        if self.get_rpcaptcache().is_installed('grub-pc'):
            grub_version = 202
            grub_fw_type.append('bios')
        if self.get_rpcaptcache().is_installed(f'grub-efi-{grub_arch}-bin'):
            grub_version = 202
            grub_tgt = 'x86_64' if self.arch == 'amd64' else self.arch
            grub_fw_type.extend(['efi', grub_tgt + '-efi'])
        if (self.get_rpcaptcache().is_installed('shim-signed') and
                self.get_rpcaptcache().is_installed(
                    f'grub-efi-{grub_arch}-signed')):
            grub_version = 202
            grub_fw_type.append('shimfix')
        if self.get_rpcaptcache().is_installed('grub-legacy'):
            logging.warning('package grub-legacy is installed, '
                            'this is obsolete.')
            grub_version = 97
            grub_fw_type.append('bios')
        elif not grub_fw_type:
            logging.warning('neither package grub-pc nor grub-efi-%s-bin '
                            'are installed, skipping grub',
                            grub_arch)

        self.targetfs.part_target(self.builddir, grub_version, grub_fw_type)

        self.build_cdroms(build_bin, build_sources, cdrom_size, tgt_pkg_lst=tgt_pkgs)

        if self.postbuild_file:
            logging.info('Postbuild script')
            do([self.postbuild_file, self.builddir,
                self.xml.text('project/version'), self.xml.text('project/name')],
               check=False)

        do_prj_finetuning(self.xml,
                          self.buildenv,
                          self.targetfs,
                          self.builddir)

        self.targetfs.pack_images(self.builddir)

        if os.path.exists(self.validationpath):
            with open(self.validationpath) as f:
                shutil.copyfileobj(f, sys.stdout)

    def pdebuild_init(self):
        # Remove pdebuilder directory, containing last build results
        do(['rm', '-rf', os.path.join(self.builddir, 'pdebuilder')])

        # Remove pbuilder/result directory
        do(['rm', '-rf',
            os.path.join(self.builddir, 'pbuilder', 'result'),
            os.path.join(self.builddir, 'pbuilder_cross', 'result')])

        # Recreate the directories removed
        if os.path.exists(os.path.join(self.builddir, 'pbuilder_cross')):
            do(['mkdir', '-p', os.path.join(self.builddir, 'pbuilder_cross', 'result')])
        else:
            do(['mkdir', '-p', os.path.join(self.builddir, 'pbuilder', 'result')])

    def pdebuild(self, profile, cross):
        cross_pbuilderrc = os.path.join(self.builddir, 'cross_pbuilderrc')
        if cross and not os.path.exists(cross_pbuilderrc):
            logging.error('Please make sure that you create the pbuilder '
                          'environment with the --cross option if you want to '
                          'use the build command with --cross.')
            sys.exit(116)

        if os.path.exists(cross_pbuilderrc) and not cross:
            logging.error('Please make sure that if you created the pbuilder '
                          'environment without the --cross option, you use the '
                          'build command without --cross too.')
            sys.exit(117)

        self.pdebuild_init()

        pbdir = os.path.join(self.builddir, 'pdebuilder', 'current')
        do(['mkdir', '-p', os.path.join(pbdir)])

        # Untar current_pdebuild.tar.gz into pdebuilder/current
        do(['tar', '--no-same-owner', '--no-same-permissions', '-xzf',
            os.path.join(self.builddir, 'current_pdebuild.tar.gz'),
            '-C', pbdir])

        self.pdebuild_build(profile, cross)
        self.repo.finalize()

    def pdebuild_build(self, profile, cross):
        profile_list = profile.split(',')
        deb_build_opts = [i for i in profile_list if i in ('nodoc', 'nocheck')]

        pdebuilder_current = os.path.join(self.builddir, 'pdebuilder', 'current')

        formatfile = ''

        if os.path.exists(os.path.join(pdebuilder_current, 'debian', 'source', 'format')):
            with open(os.path.join(pdebuilder_current, 'debian', 'source', 'format'), 'r') as f:
                formatfile = f.read()

        with open(os.path.join(pdebuilder_current, 'debian', 'changelog'), 'r') as f:
            src_pkg_name = Changelog(f).get_package()

        orig_files = glob.glob(os.path.join(self.builddir, f'{src_pkg_name}*.orig.*'))

        if '3.0 (quilt)' in formatfile and not orig_files:
            do(['origtargz', '--download-only', '--tar-only'], cwd=pdebuilder_current)
        else:
            for orig_fname in orig_files:
                do(['mv', orig_fname, os.path.join(self.builddir, 'pdebuilder')])

        try:
            debuild_env = {
                'DEBUILD_DPKG_BUILDPACKAGE_OPTS': '-sa -jauto',
                'DEB_BUILD_PROFILES': profile.replace(',', ' '),
                'DEB_BUILD_OPTIONS': ' '.join(deb_build_opts),
            }

            if cross:
                do(['dpkg-source', '-b', '.'],
                   cwd=os.path.join(self.builddir, 'pdebuilder', 'current'),
                   env_add=debuild_env)
                do(['pbuilder', 'build', '--host-arch', self.arch,
                    '--configfile', os.path.join(self.builddir, 'cross_pbuilderrc'),
                    '--debbuildopts', '-sa',
                    '--basetgz', os.path.join(self.builddir, 'pbuilder_cross', 'base.tgz'),
                    '--buildresult', os.path.join(self.builddir, 'pbuilder_cross', 'result'),
                    *glob.glob('../*.dsc',
                               root_dir=os.path.join(self.builddir, 'pdebuilder', 'current'))],
                   cwd=os.path.join(self.builddir, 'pdebuilder', 'current'),
                   env_add=debuild_env)
                pbuilderdir = 'pbuilder_cross'
            else:
                do(['pdebuild',
                    '--configfile', os.path.join(self.builddir, 'pbuilderrc'),
                    '--debbuildopts', '-sa',
                    '--use-pdebuild-internal',
                    '--buildresult', os.path.join(self.builddir, 'pbuilder', 'result')],
                   cwd=os.path.join(self.builddir, 'pdebuilder', 'current'),
                   env_add=debuild_env)
                pbuilderdir = 'pbuilder'

            self.repo.remove(os.path.join(self.builddir,
                                          'pdebuilder',
                                          'current',
                                          'debian',
                                          'control'))

            for changes in glob.glob(os.path.join(self.builddir,
                                                  pbuilderdir, 'result', '*.changes')):
                self.repo.include(changes)

        except subprocess.CalledProcessError:
            logging.exception('Package fails to build.\n'
                              'Please make sure, that the submitted package '
                              'builds in pbuilder')

    def update_pbuilder(self):
        do(['pbuilder', '--update',
            '--configfile', os.path.join(self.builddir, 'pbuilderrc'),
            '--aptconfdir', os.path.join(self.builddir, 'aptconfdir')])

    def create_pbuilder(self, cross, noccache, ccachesize):
        # Remove old pbuilder directory, if it exists
        do(['rm', '-rf',
            os.path.join(self.builddir, 'pbuilder'),
            os.path.join(self.builddir, 'pbuilder_cross')])

        # make hooks.d and pbuilder directory
        if cross:
            do(['mkdir', '-p', os.path.join(self.builddir, 'pbuilder_cross', 'hooks.d')])
            do(['mkdir', '-p', os.path.join(self.builddir, 'pbuilder_cross', 'aptcache')])
        else:
            do(['mkdir', '-p', os.path.join(self.builddir, 'pbuilder', 'hooks.d')])
            do(['mkdir', '-p', os.path.join(self.builddir, 'pbuilder', 'aptcache')])

        do(['mkdir', '-p', os.path.join(self.builddir, 'aptconfdir', 'apt.conf.d')])

        if not noccache:
            ccache_path = os.path.join(self.builddir, 'ccache')
            do(['mkdir', '-p', ccache_path])
            do(['chmod', 'a+w', ccache_path])
            ccache_fp = open(os.path.join(ccache_path, 'ccache.conf'), 'w')
            ccache_fp.write(f'max_size = {ccachesize}')
            ccache_fp.close()

        # write config files
        if cross:
            pbuilder_write_cross_config(self.builddir, self.xml, noccache)
            pbuilder_write_repo_hook(self.builddir, self.xml, cross)
            do(['chmod', '-R', '755', os.path.join(self.builddir, 'pbuilder_cross', 'hooks.d')])
        else:
            pbuilder_write_config(self.builddir, self.xml, noccache)
            pbuilder_write_repo_hook(self.builddir, self.xml, cross)
            do(['chmod', '-R', '755', os.path.join(self.builddir, 'pbuilder', 'hooks.d')])
        pbuilder_write_apt_conf(self.builddir, self.xml)

        # Run pbuilder --create
        no_check_gpg = []
        keyring = []
        debootstrap_key_path = pbuilder_get_debootstrap_key_path(self.chrootpath, self.xml)
        if self.xml.prj.has('noauth'):
            no_check_gpg = ['--debootstrapopts', '--no-check-gpg']
        elif debootstrap_key_path:
            keyring = ['--debootstrapopts', '--keyring=' + debootstrap_key_path]
        if cross:
            do(['pbuilder', '--create',
                '--buildplace', os.path.join(self.builddir, 'pbuilder_cross'),
                '--configfile', os.path.join(self.builddir, 'cross_pbuilderrc'),
                '--aptconfdir', os.path.join(self.builddir, 'aptconfdir'),
                '--debootstrapopts', '--include=git,gnupg', *no_check_gpg, *keyring])
        else:
            do(['pbuilder', '--create',
                '--configfile', os.path.join(self.builddir, 'pbuilderrc'),
                '--aptconfdir', os.path.join(self.builddir, 'aptconfdir'),
                '--debootstrapopts', '--include=git,gnupg', *no_check_gpg, *keyring])

    def sync_xml_to_disk(self):
        try:
            sourcexmlpath = os.path.join(self.builddir, 'source.xml')
            self.xml.xml.write(sourcexmlpath)
        except MemoryError:
            logging.exception('write source.xml failed (archive to huge?)')

    def get_rpcaptcache(self, env=None, norecommend=None):
        if not env:
            env = self.buildenv

        if norecommend is None:
            norecommend = not self.xml.prj.has('install-recommends')

        if env.arch == 'default':
            arch = self.arch
        else:
            arch = env.arch

        if env.rpcaptcache is None:
            env.rpcaptcache = get_rpcaptcache(env.rfs, arch,
                                              norecommend,
                                              self.xml.prj.has('noauth'))
        return env.rpcaptcache

    def drop_rpcaptcache(self, env=None):
        if not env:
            env = self.buildenv
        env.rpcaptcache = None

    def has_full_buildenv(self):
        if os.path.exists(self.chrootpath):
            elbeversionpath = os.path.join(self.chrootpath,
                                           'etc', 'elbe_version')
            if os.path.isfile(elbeversionpath):
                return True

            logging.warning('%s exists, but it does not have '
                            'an etc/elbe_version file.', self.chrootpath)
            # Apparently we do not have a functional build environment
            return False

        return False

    def set_xml(self, xmlpath):
        # Use supplied XML file, if given, otherwise change to source.xml
        if not xmlpath:
            xmlpath = os.path.join(self.builddir, 'source.xml')

        newxml = ElbeXML(xmlpath, buildtype=self.override_buildtype,
                         skip_validate=self.skip_validate,
                         url_validation=self.url_validation)

        # New XML file has to have the same architecture
        oldarch = self.xml.text('project/arch', key='arch')
        newarch = newxml.text('project/arch', key='arch')
        if newarch != oldarch:
            raise IncompatibleArchitectureException(oldarch, newarch)

        # Throw away old APT cache, targetfs and buildenv
        self.targetfs = None
        self.buildenv = None

        # don't create sysroot instance, it should be built from scratch
        # each time, because the pkglist including the -dev packages is
        # tracked nowhere.
        self.sysrootenv = None
        do(['rm', '-rf', self.sysrootpath])

        self.xml = newxml

        # Create a new BuildEnv instance, if we have a build directory
        if self.has_full_buildenv():
            self.buildenv = BuildEnv(self.xml,
                                     self.chrootpath,
                                     clean=False)

        # Create TargetFs instance, if the target directory exists.
        # We use the old content of the directory if no rebuild is done, so
        # don't clean it (yet).
        if os.path.exists(self.targetpath):
            self.targetfs = TargetFs(self.targetpath, self.xml,
                                     clean=False)
        else:
            self.targetfs = None

    def write_log_header(self):

        logging.info('ELBE Report for Project %s\n'
                     'Report timestamp: %s\n'
                     'elbe: %s',
                     self.name,
                     datetime.datetime.now().strftime('%Y%m%d-%H%M%S'),
                     str(elbe_version))

    def copy_initvmnode(self):
        source_path = '/var/cache/elbe/source.xml'
        try:
            initxml = ElbeXML(source_path,
                              skip_validate=self.skip_validate,
                              url_validation=ValidationMode.NO_CHECK)
            self.xml.get_initvmnode_from(initxml)
        except ValidationError:
            logging.exception('%s validation failed.  '
                              'Will not copy initvm node', source_path)
        except IOError:
            logging.exception('%s not available.  '
                              'Can not copy initvm node', source_path)
        except NoInitvmNode:
            logging.exception('%s is available.  But it does not '
                              'contain an initvm node', source_path)

    def install_packages(self, target, buildenv=False):

        # to workaround debian bug no. 872543
        if self.xml.prj.has('noauth'):
            inrelease = glob.glob(f'{self.chrootpath}/var/lib/apt/lists/*InRelease')
            release_gpg = glob.glob(f'{self.chrootpath}/var/lib/apt/lists/*.gpg')
            if inrelease:
                os.remove(inrelease[0])
                logging.info('Removed InRelease file!')
            if release_gpg:
                os.remove(release_gpg[0])
                logging.info('Removed Release.gpg file!')

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

                self.copy_initvmnode()
            else:
                sourcepath = os.path.join(self.builddir, 'source.xml')
                source = ElbeXML(sourcepath,
                                 buildtype=self.override_buildtype,
                                 skip_validate=self.skip_validate,
                                 url_validation=self.url_validation)

                self.xml.get_debootstrappkgs_from(source)
                try:
                    self.xml.get_initvmnode_from(source)
                except NoInitvmNode:
                    logging.warning('source.xml is available. '
                                    'But it does not contain an initvm node')
                    self.copy_initvmnode()

            # Seed /etc, we need /etc/hosts for hostname -f to work correctly
            if not buildenv:
                target.seed_etc()

            # remove all non-essential packages to ensure that on a incremental
            # build packages can be removed
            debootstrap_pkgs = []
            for p in self.xml.node('debootstrappkgs'):
                debootstrap_pkgs.append(p.et.text)

            pkgs = target.xml.get_target_packages() + debootstrap_pkgs

            if buildenv:
                pkgs = pkgs + target.xml.get_buildenv_packages()

            # Now install requested packages
            for p in pkgs:
                try:
                    self.get_rpcaptcache(env=target).mark_install(p, None)
                except KeyError:
                    logging.exception('No Package %s', p)
                except SystemError:
                    logging.exception('Unable to correct problems '
                                      'in package %s',
                                      p)

            # temporary disabled because of
            # https://bugs.debian.org/cgi-bin/bugreport.cgi?bug=776057
            # the functions cleans up to much
            # self.get_rpcaptcache().cleanup(debootstrap_pkgs + pkgs)

            self.get_rpcaptcache(env=target).fetch_archives()

            # The package installation below may want to manage resolv.conf.
            target.rfs.end_excursion('/etc/resolv.conf')

            try:
                self.get_rpcaptcache(env=target).commit()
            except SystemError as e:
                logging.exception('Commiting changes failed')
                raise AptCacheCommitError(str(e))

    def gen_licenses(self, rfs, env, pkg_list):

        lic_txt_fname = os.path.join(self.builddir, f'licence-{rfs}.txt')
        lic_xml_fname = os.path.join(self.builddir, f'licence-{rfs}.xml')
        pkg_list.sort()

        with io.open(lic_txt_fname, 'w+',
                     encoding='utf-8', errors='replace') as f:
            env.rfs.write_licenses(f, pkg_list, lic_xml_fname)
