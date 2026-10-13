# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2014-2018 Linutronix GmbH

import os
import sys
import time
from multiprocessing.managers import BaseManager
from multiprocessing.util import Finalize

from apt import Cache

from apt_pkg import config

from elbepack.aptpkgutils import (
    APTPackage,
    fetch_source,
    get_corresponding_source_packages,
    getalldeps,
)
from elbepack.aptprogress import (
    ElbeAcquireProgress,
    ElbeInstallProgress,
    ElbeOpProgress,
)
from elbepack.log import async_logging


class MyMan(BaseManager):

    @staticmethod
    def register(typeid):
        """Register to BaseManager through decorator"""
        def _register(cls):
            BaseManager.register(typeid, cls)
            return cls
        return _register

    @staticmethod
    def redirect_outputs(w):
        """Redirect all outputs to the writing end of a pipe 'w'"""
        os.dup2(w, sys.stdout.fileno())
        os.dup2(w, sys.stderr.fileno())
        # Buffering of 1 because in Python3 buffering of 0 is illegal
        # for non binary mode ..
        sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', 1)
        sys.stderr = os.fdopen(sys.stderr.fileno(), 'w', 1)
        sys.__stdout__ = sys.stdout  # type: ignore
        sys.__stderr__ = sys.stderr  # type: ignore

    def start(self):
        """Redirect outputs of the process to an async logging thread"""
        alog = async_logging()
        self.log_finalizer = Finalize(self, alog.shutdown)
        super().start(MyMan.redirect_outputs, [alog.write_fd])


class InChRootObject:
    def __init__(self, rfs):
        self.rfs = rfs
        self.rfs.enter_chroot()
        self.finalizer = Finalize(self, self.rfs.leave_chroot, exitpriority=10)


@MyMan.register('RPCAPTCache')
class RPCAPTCache(InChRootObject):

    def __init__(self, rfs, arch, norecommend=False, noauth=True):

        super().__init__(rfs)

        config.set('APT::Architecture', arch)
        if norecommend:
            config.set('APT::Install-Recommends', '0')
        else:
            config.set('APT::Install-Recommends', '1')

        if noauth:
            config.set('APT::Get::AllowUnauthenticated', '1')
        else:
            config.set('APT::Get::AllowUnauthenticated', '0')

        config.set('Acquire::Retries', '10')
        config.set('Acquire::Retries::Delay', 'true')
        config.set('Acquire::Retries::Delay::Maximum', '30')
        config.set('Debug::pkgProblemResolver', '1')

        self.cache = Cache(progress=ElbeOpProgress())
        self.cache.open(progress=ElbeOpProgress())

    def dbg_dump(self, filename):
        ts = time.localtime()
        with open(f'{filename}_{ts.tm_hour:02}{ts.tm_min:02}{ts.tm_sec:02}', 'w') as dbg:
            for p in self.cache:
                dbg.write(
                    f'{p.name} {p.candidate.version} {p.marked_keep} '
                    f'{p.marked_delete} {p.marked_upgrade} '
                    f' {p.marked_downgrade} {p.marked_install} '
                    f' {p.marked_reinstall} {p.is_auto_installed} '
                    f' {p.is_installed} {p.is_auto_removable} '
                    f'{p.is_now_broken} {p.is_inst_broken} '
                    f'{p.is_upgradable}\n')

    def mark_install(self, pkgname, version, from_user=True, nodeps=False):
        print(f'Mark for install "{pkgname}"')
        p = self.cache[pkgname]
        if version:
            p.candidate = p.versions[version]
        p.mark_install(auto_fix=not nodeps,
                       auto_inst=not nodeps,
                       from_user=from_user)

    def mark_install_devpkgs(self, ignore_pkgs, ignore_dev_pkgs):

        # we don't want to ignore libc
        ignore_pkgs.discard('libc6')
        ignore_pkgs.discard('libstdc++5')
        ignore_pkgs.discard('libstdc++6')

        # list all debian src packages of all installed packages that
        # don't come from debootstrap
        src_name_lst = []
        version_dict = {}

        for pkg in self.cache:
            if pkg.is_installed and pkg.name not in ignore_pkgs:
                src_name = pkg.candidate.source_name
                src_name_lst.append(src_name)
                version_dict[pkg.name] = pkg.candidate.version
                version_dict[src_name] = pkg.candidate.source_version

        def mark_install(pkg_lst, suffix):

            for pkg in pkg_lst:

                if pkg.name in ignore_dev_pkgs:
                    continue

                name_no_suffix = pkg.name[:-len(suffix)]

                if name_no_suffix in version_dict:

                    version = version_dict[name_no_suffix]
                    candidate = pkg.versions.get(version)

                    if candidate:
                        pkg.candidate = candidate

                pkg.mark_install()

        # go through all packages, remember package if its source
        # package matches one of the installed packages and the binary
        # package is a '-dev' package
        dev_lst = []

        for pkg in self.cache:

            if not pkg.name.endswith('-dev'):
                continue

            src_name = pkg.candidate.source_name

            if src_name not in version_dict:
                continue

            src_version = pkg.candidate.source_version

            if src_version != version_dict[src_name]:
                continue

            dev_lst.append(pkg)

        mark_install(dev_lst, '-dev')

        # ensure that the symlinks package will be installed (it's
        # needed for fixing links inside the sysroot
        self.cache['symlinks'].mark_install()

        for pkg in ignore_dev_pkgs:
            self.cache[pkg].mark_delete()

        dbgsym_lst = []

        for pkg in self.cache:

            if pkg.is_installed or pkg.marked_install:

                dbg_pkg = f'{pkg.name}-dbgsym'

                if dbg_pkg in self.cache:
                    dbgsym_lst.append(self.cache[dbg_pkg])

        mark_install(dbgsym_lst, '-dbgsym')

    def cleanup(self, exclude_pkgs):
        for p in self.cache:
            if p.is_installed and not \
               p.is_auto_installed or \
               p.is_auto_removable:
                remove = True
                for x in exclude_pkgs:
                    if x == p.name:
                        remove = False
                if remove:
                    p.mark_delete(auto_fix=True, purge=True)

    def mark_delete(self, pkgname):
        p = self.cache[pkgname]
        p.mark_delete(purge=True)

    def update(self):
        self.cache.update(fetch_progress=ElbeAcquireProgress())
        self.cache.open(progress=ElbeOpProgress())

    def fetch_archives(self):
        print('Fetching packages...')
        self.cache.fetch_archives(ElbeAcquireProgress())

    def commit(self):
        os.environ['DEBIAN_FRONTEND'] = 'noninteractive'
        os.environ['DEBONF_NONINTERACTIVE_SEEN'] = 'true'
        print('Commiting changes ...')
        self.cache.commit(ElbeAcquireProgress(),
                          ElbeInstallProgress(fileno=sys.stdout.fileno()))
        self.cache.open(progress=ElbeOpProgress())

    def get_dependencies(self, pkgname, blacklist):
        deps = getalldeps(self.cache, pkgname, blacklist)
        return [APTPackage(self.cache[p]) for p in deps]

    def get_installed_pkgs(self, section='all'):
        if section == 'all':
            pl = [APTPackage(p) for p in self.cache if p.is_installed]
        else:
            pl = [APTPackage(p) for p in self.cache if (
                p.section == section and p.is_installed)]
        return pl

    def get_fileindex(self, removeprefix=None):
        """
        Returns a map filepath => packagename indexed by the filepath.
        Use removeprefix to remove any prefix from the actual filepath.
        """
        index = {}

        for p in self.cache:
            if p.is_installed:
                for f in p.installed_files:
                    if removeprefix and f.startswith(removeprefix):
                        unprefixed = f[len(removeprefix):]
                    else:
                        unprefixed = f
                    index[unprefixed] = p.name

        return index

    def has_pkg(self, pkgname):
        return pkgname in self.cache

    def is_installed(self, pkgname):
        if pkgname not in self.cache:
            return False
        return self.cache[pkgname].is_installed

    def get_pkg(self, pkgname):
        return APTPackage(self.cache[pkgname])

    def get_corresponding_source_packages(self, pkg_lst=None, *, include_built_using=True):
        return get_corresponding_source_packages(self.cache, pkg_lst, include_built_using)

    def download_binary(self, pkgname, path, version=None):
        p = self.cache[pkgname]
        if version is None:
            pkgver = p.installed
        else:
            pkgver = p.versions[version]
        rel_filename = pkgver.fetch_binary(path, ElbeAcquireProgress())
        return self.rfs.fname(rel_filename)

    def download_source(self, src_name, src_version, dest_dir):
        return self.rfs.fname(fetch_source(src_name, src_version, dest_dir, ElbeAcquireProgress()))


def get_rpcaptcache(rfs, arch, norecommend=False, noauth=True):

    mm = MyMan()
    mm.start()

    # Disable false positive, because pylint can not
    # see the creation of MyMan.RPCAPTCache by
    # MyMan.register()
    #
    return mm.RPCAPTCache(rfs, arch, norecommend, noauth)
