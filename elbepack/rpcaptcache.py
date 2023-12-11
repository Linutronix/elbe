# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2014-2018 Linutronix GmbH

import logging
import os
import sys
import time

from multiprocessing.util import Finalize
from multiprocessing.managers import BaseManager

from apt_pkg import config, version_compare, TagFile, SourceRecords, Acquire, AcquireFile
from apt import Cache
from apt.package import FetchError

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


class InChRootObject:
    def __init__(self, rfs):
        self.rfs = rfs
        self.rfs.enter_chroot()
        self.finalizer = Finalize(self, self.rfs.leave_chroot, exitpriority=10)


@MyMan.register("RPCAPTCache")
class RPCAPTCache(InChRootObject):

    def __init__(self, rfs, arch,
                 notifier=None, norecommend=False, noauth=True):

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
        with open(f'{filename}_{ts.tm_hour:02}{ts.tm_min:02}{ts.tm_sec:02}', 'w') as dbg:
            for p in self.cache:
                dbg.write(
                    f"{p.name} {p.candidate.version} {p.marked_keep} "
                    f"{p.marked_delete} {p.marked_upgrade} "
                    f" {p.marked_downgrade} {p.marked_install} "
                    f" {p.marked_reinstall} {p.is_auto_installed} "
                    f" {p.is_installed} {p.is_auto_removable} "
                    f"{p.is_now_broken} {p.is_inst_broken} "
                    f"{p.is_upgradable}\n")

    def get_sections(self):
        ret = list({p.section for p in self.cache})
        ret.sort()
        return ret

    def get_pkglist(self, section):
        if section == 'all':
            ret = [APTPackage(p) for p in self.cache]
        else:
            ret = [APTPackage(p) for p in self.cache if p.section == section]

        return ret

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
                version_dict[src_name] = pkg.candidate.version

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

            if not pkg.name.endswith("-dev"):
                continue

            src_name = pkg.candidate.source_name

            if src_name not in version_dict:
                continue

            src_version = pkg.candidate.source_version

            if src_version != version_dict[src_name]:
                continue

            dev_lst.append(pkg)

        mark_install(dev_lst, "-dev")

        # ensure that the symlinks package will be installed (it's
        # needed for fixing links inside the sysroot
        self.cache['symlinks'].mark_install()

        for pkg in ignore_dev_pkgs:
            self.cache[pkg].mark_delete()

        dbgsym_lst = []

        for pkg in self.cache:

            if pkg.is_installed or pkg.marked_install:

                dbg_pkg = f"{pkg.name}-dbgsym"

                if dbg_pkg in self.cache:
                    dbgsym_lst.append(self.cache[dbg_pkg])

        mark_install(dbgsym_lst, "-dbgsym")

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

    def mark_keep(self, pkgname, _version):
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

    @staticmethod
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

    def download_source(self, src_name, src_version, dest_dir):

        allow_untrusted = config.find_b("APT::Get::AllowUnauthenticated",
                                        False)

        rec = SourceRecords()
        acq = Acquire(ElbeAcquireProgress())

        # poorman's iterator
        while True:
            next_p = rec.lookup(src_name)
            # End of the list?
            if not next_p:
                raise ValueError(
                    f"No source found for {src_name}_{src_version}")
            if src_version == rec.version:
                break

        # We don't allow untrusted package and the package is not
        # marks as trusted
        if not (allow_untrusted or rec.index.is_trusted):
            raise FetchError(
                f"Can't fetch source {src_name}_{src_version}; "
                f"Source {rec.index.describe} is not trusted")

        # Copy from src to dst all files of the source package
        dsc = None
        files = []
        for _file in rec.files:
            src = os.path.basename(_file.path)
            dst = os.path.join(dest_dir, src)

            if 'dsc' == _file.type:
                dsc = dst

            if not (allow_untrusted or _file.hashes.usable):
                raise FetchError(
                    f"Can't fetch file {dst}. No trusted hash found.")

            # acq is accumlating the AcquireFile, the files list only
            # exists to prevent Python from GC the object .. I guess.
            # Anyway, if we don't keep the list, We will get an empty
            # directory
            files.append(AcquireFile(acq, rec.index.archive_uri(_file.path),
                                     _file.hashes, _file.size, src, destfile=dst))
        acq.run()

        if dsc is None:
            raise ValueError(f"No source found for {src_name}_{src_version}")

        for item in acq.items:
            if item.STAT_DONE != item.status:
                raise FetchError(
                    f"Can't fetch item {item.destfile}: {item.error_text}")

        return self.rfs.fname(os.path.abspath(dsc))


def get_rpcaptcache(rfs, arch,
                    notifier=None, norecommend=False, noauth=True):

    mm = MyMan()
    mm.start()

    # Disable false positive, because pylint can not
    # see the creation of MyMan.RPCAPTCache by
    # MyMan.register()
    #
    return mm.RPCAPTCache(rfs, arch, notifier, norecommend, noauth)
