# ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (c) 2014 Markus Kreidl <mkreidl@linutronix.de>
# Copyright (c) 2014, 2016 Torben Hohn <torben.hohn@linutronix.de>
# Copyright (c) 2014 Stefan Gast <stefan.gast@linutronix.de>
# Copyright (c) 2014-2018 Manuel Traut <manut@linutronix.de>
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import print_function

import logging
import os
import sys
import time

from multiprocessing.util import Finalize
from multiprocessing.managers import BaseManager

from apt_pkg import config, version_compare, TagFile
from apt import Cache

from elbepack.aptprogress import (ElbeAcquireProgress, ElbeInstallProgress,
                                  ElbeOpProgress)
from elbepack.aptpkgutils import getalldeps, APTPackage, fetch_binary
from elbepack.log import async_logging


log = logging.getLogger("log")
soap = logging.getLogger("soap")


class MyMan(BaseManager):

    @staticmethod
    def register(typeid):
        """Register to BaseManager through decorator"""
        def _register(cls):
            BaseManager.register(typeid, cls)
            return cls
        return _register

    @staticmethod
    def redirect_outputs(r, w):
        """Redirect all outputs to the writing end of a pipe 'w'"""
        os.close(r)
        os.dup2(w, os.sys.stdout.fileno())
        os.dup2(w, os.sys.stderr.fileno())
        # Buffering of 1 because in Python3 buffering of 0 is illegal
        # for non binary mode ..
        os.sys.stdout = os.fdopen(os.sys.stdout.fileno(), "w", 1)
        os.sys.stderr = os.fdopen(os.sys.stderr.fileno(), "w", 1)
        os.sys.__stdout__ = os.sys.stdout
        os.sys.__stderr__ = os.sys.stderr

    def start(self):
        """Redirect outputs of the process to an async logging thread"""
        r, w = os.pipe()
        super(MyMan, self).start(MyMan.redirect_outputs, [r, w])
        async_logging(r, w, soap, log)


class InChRootObject(object):
    def __init__(self, rfs):
        self.rfs = rfs
        self.rfs.enter_chroot()
        self.finalizer = Finalize(self, self.rfs.leave_chroot, exitpriority=10)


@MyMan.register("RPCAPTCache")
class RPCAPTCache(InChRootObject):

    # pylint: disable=too-many-public-methods
    def __init__(self, rfs, arch,
                 notifier=None, norecommend=False, noauth=True):

        # pylint: disable=too-many-arguments
        InChRootObject.__init__(self, rfs)

        self.notifier = notifier
        config.set("APT::Architecture", arch)
        if norecommend:
            config.set("APT::Install-Recommends", "0")
        else:
            config.set("APT::Install-Recommends", "1")

        if noauth:
            config.set("APT::Get::AllowUnauthenticated", "1")
        else:
            config.set("APT::Get::AllowUnauthenticated", "0")

        self.cache = Cache(progress=ElbeOpProgress())
        self.cache.open(progress=ElbeOpProgress())

    def dbg_dump(self, filename):
        ts = time.localtime()
        filename = filename + (
            '_%02d%02d%02d' % (ts.tm_hour, ts.tm_min, ts.tm_sec))
        with open(filename, 'w') as dbg:
            for p in self.cache:
                dbg.write(
                    '%s %s %d %d %d %d %d %d %d %d %d %d %d %d\n' %
                    (p.name,
                     p.candidate.version,
                     p.marked_keep,
                     p.marked_delete,
                     p.marked_upgrade,
                     p.marked_downgrade,
                     p.marked_install,
                     p.marked_reinstall,
                     p.is_auto_installed,
                     p.is_installed,
                     p.is_auto_removable,
                     p.is_now_broken,
                     p.is_inst_broken,
                     p.is_upgradable))

    def get_sections(self):
        ret = list(set([p.section for p in self.cache]))
        ret.sort()
        return ret

    def get_pkglist(self, section):
        if section == 'all':
            ret = [APTPackage(p) for p in self.cache]
        else:
            ret = [APTPackage(p) for p in self.cache if p.section == section]

        return ret

    def mark_install(self, pkgname, version, from_user=True, nodeps=False):
        print('Mark for install "%s"' % pkgname)
        p = self.cache[pkgname]
        if version:
            p.candidate = p.versions[version]
        p.mark_install(auto_fix=not nodeps,
                       auto_inst=not nodeps,
                       from_user=from_user)

    def mark_install_devpkgs(self, ignore_pkgs, ignore_dev_pkgs):
        ignore_pkgs.discard('libc6')  # we don't want to ignore libc
        ignore_pkgs.discard('libstdc++5')
        ignore_pkgs.discard('libstdc++6')
        # list all debian src packages of all installed packages that don't
        # come from debootstrap
        src_list = [
            p.candidate.source_name for p in self.cache if (
                p.is_installed and p.name not in ignore_pkgs)]
        version_dict = {
            p.name: p.candidate.version for p in self.cache if (
                p.is_installed and p.name not in ignore_pkgs)}
        # go through all packages, remember package if its source package
        # matches one of the installed packages and the binary package is a
        # '-dev' package
        dev_list = [
            s for s in self.cache if (
                s.candidate.source_name in src_list and (
                    s.name.endswith('-dev')))]
        for p in dev_list:
            if p.name not in ignore_dev_pkgs:
                name_no_suffix = p.name[:-len('-dev')]
                if name_no_suffix in version_dict:
                    version = version_dict[name_no_suffix]
                    candidate = p.versions.get(version)
                    if candidate:
                        p.candidate = candidate
                p.mark_install()
        # ensure that the symlinks package will be installed (it's needed for
        # fixing links inside the sysroot
        self.cache['symlinks'].mark_install()

        for p in ignore_dev_pkgs:
            self.cache[p].mark_delete()

        dbgsym_list = [
                s.name + '-dbgsym' for s in self.cache if (
                    s.is_installed or s.marked_install)]

        for p in dbgsym_list:
            if p in self.cache:
                pkg = self.cache[p]
                name_no_suffix = pkg.name[:-len('-dbgsym')]
                if name_no_suffix in version_dict:
                    version = version_dict[name_no_suffix]
                    candidate = pkg.versions.get(version)
                    if candidate:
                        pkg.candidate = candidate
                pkg.mark_install()

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

    def mark_upgrade(self, pkgname, version):
        p = self.cache[pkgname]
        if version:
            p.candidate = p.versions[version]
        p.mark_upgrade()

    def mark_delete(self, pkgname):
        p = self.cache[pkgname]
        p.mark_delete(purge=True)

    def mark_keep(self, pkgname, version):
        p = self.cache[pkgname]
        p.mark_keep()

    def update(self):
        self.cache.update(fetch_progress=ElbeAcquireProgress())
        self.cache.open(progress=ElbeOpProgress())

    def commit(self):
        os.environ["DEBIAN_FRONTEND"] = "noninteractive"
        os.environ["DEBONF_NONINTERACTIVE_SEEN"] = "true"
        print("Commiting changes ...")
        self.cache.commit(ElbeAcquireProgress(),
                          ElbeInstallProgress(fileno=sys.stdout.fileno()))
        self.cache.open(progress=ElbeOpProgress())

    def clear(self):
        self.cache.clear()

    def get_dependencies(self, pkgname):
        deps = getalldeps(self.cache, pkgname)
        return [APTPackage(p, cache=self.cache) for p in deps]

    def get_installed_pkgs(self, section='all'):
        if section == 'all':
            pl = [APTPackage(p) for p in self.cache if p.is_installed]
        else:
            pl = [APTPackage(p) for p in self.cache if (
                p.section == section and p.is_installed)]
        return pl

    def get_fileindex(self):
        index = {}

        for p in self.cache:
            if p.is_installed:
                for f in p.installed_files:
                    index[f] = p.name

        return index

    def get_marked_install(self, section='all'):
        if section == 'all':
            ret = [APTPackage(p) for p in self.cache if p.marked_install]
        else:
            ret = [APTPackage(p) for p in self.cache if (p.section == section
                                                         and p.marked_install)]
        return ret

    def get_upgradeable(self, section='all'):
        if section == 'all':
            ret = [APTPackage(p) for p in self.cache if p.is_upgradable]
        else:
            ret = [APTPackage(p) for p in self.cache if (p.section == section
                                                         and p.is_upgradable)]
        return ret

    def upgrade(self, dist_upgrade=False):
        self.cache.upgrade(dist_upgrade)

    def get_changes(self):
        changes = self.cache.get_changes()
        return [APTPackage(p) for p in changes]

    def has_pkg(self, pkgname):
        return pkgname in self.cache

    def is_installed(self, pkgname):
        if pkgname not in self.cache:
            return False
        return self.cache[pkgname].is_installed

    def get_pkg(self, pkgname):
        return APTPackage(self.cache[pkgname])

    def get_pkgs(self, pkgname):
        return [
            APTPackage(
                self.cache[p]) for p in sorted(
                self.cache.keys()) if pkgname in p.lower()]

    def get_corresponding_source_packages(self, pkg_lst=None):

        if pkg_lst is None:
            pkg_lst = {p.name for p in self.cache if p.is_installed}

        src_set = set()

        with TagFile('/var/lib/dpkg/status') as tagfile:
            for section in tagfile:

                pkg = section['Package']

                if pkg not in pkg_lst:
                    continue

                tmp = self.cache[pkg].installed or self.cache[pkg].candidate

                src_set.add((tmp.source_name, tmp.source_version))

                if "Built-Using" not in section:
                    continue

                built_using_lst = section["Built-Using"].split(', ')
                for built_using in built_using_lst:
                    name, version = built_using.split(' ', 1)
                    version = version.strip('(= )')
                    src_set.add((name, version))

        return list(src_set)

    def compare_versions(self, ver1, ver2):
        return version_compare(ver1, ver2)

    def download_binary(self, pkgname, path, version=None):
        p = self.cache[pkgname]
        if version is None:
            pkgver = p.installed
        else:
            pkgver = p.versions[version]
        rel_filename = fetch_binary(pkgver,
                                    path,
                                    ElbeAcquireProgress())
        return self.rfs.fname(rel_filename)

    def download_source(self, pkgname, path, version=None):
        p = self.cache[pkgname]
        if version is None:
            pkgver = p.installed
        else:
            pkgver = p.versions[version]

        rel_filename = pkgver.fetch_source(path,
                                           ElbeAcquireProgress(),
                                           unpack=False)
        return self.rfs.fname(rel_filename)

def get_rpcaptcache(rfs, arch,
                    notifier=None, norecommend=False, noauth=True):

    # pylint: disable=too-many-arguments

    mm = MyMan()
    mm.start()

    # Disable false positive, because pylint can not
    # see the creation of MyMan.RPCAPTCache by
    # MyMan.register()
    #
    # pylint: disable=no-member
    return mm.RPCAPTCache(rfs, arch, notifier, norecommend, noauth)
