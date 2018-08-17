# ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (c) 2014-2016 Torben Hohn <torben.hohn@linutronix.de>
# Copyright (c) 2014-2015, 2017 Manuel Traut <manut@linutronix.de>
# Copyright (c) 2016 John Ogness <john.ogness@linutronix.de>
# Copyright (c) 2017 Philipp Arras <philipp.arras@linutronix.de>
#
# SPDX-License-Identifier: GPL-3.0-or-later

import os

from apt.package import FetchError
from elbepack.rpcaptcache import get_rpcaptcache
from elbepack.repomanager import CdromSrcRepo
from elbepack.repomanager import CdromBinRepo
from elbepack.repomanager import CdromInitRepo
from elbepack.aptpkgutils import XMLPackage
from elbepack.aptprogress import ElbeAcquireProgress
from elbepack.filesystem import Filesystem, hostfs
from elbepack.dump import get_initvm_pkglist
from apt import Cache

CDROM_SIZE = 640 * 1000 * 1000


def mk_source_cdrom(
        rfs,
        arch,
        codename,
        init_codename,
        target,
        log,
        cdrom_size=CDROM_SIZE,
        xml=None):

    hostfs.mkdir_p('/var/cache/elbe/sources')
    rfs.mkdir_p('/var/cache/elbe/sources')

    if not xml is None:
        mirror = xml.get_primary_mirror (rfs.fname("cdrom"))
    else:
        mirror='http://ftp.de.debian.org/debian'

    repo = CdromSrcRepo(codename, init_codename,
                        os.path.join(target, "srcrepo"),
                        log,
                        cdrom_size,
                        mirror)

    cache = get_rpcaptcache(rfs, "aptcache.log", arch)
    cache.update()
    pkglist = cache.get_installed_pkgs()

    forbiddenPackages = []
    if xml is not None and xml.has('target/pkg-list'):
        for i in xml.node('target/pkg-list'):
            try:
                if i.tag == 'pkg' and i.et.attrib['on_src_cd'] == 'False':
                    forbiddenPackages.append(i.text('.').strip())

            except KeyError:
                pass

    for pkg in pkglist:
        # Do not include forbidden packages in src cdrom
        if pkg.name in forbiddenPackages:
            continue
        try:
            dsc = cache.download_source(pkg.name, '/var/cache/elbe/sources')
            repo.includedsc(dsc, force=True)
        except ValueError:
            log.printo(
                "No sources for Package " +
                pkg.name +
                "-" +
                pkg.installed_version)
        except FetchError:
            log.printo(
                "Source for Package " +
                pkg.name +
                "-" +
                pkg.installed_version +
                " could not be downloaded")

    repo.finalize()

    pkglist = get_initvm_pkglist()
    cache = Cache()
    cache.open()

    for pkg in pkglist:
        # Do not include forbidden packages in src cdrom
        if pkg.name in forbiddenPackages:
            continue
        try:
            p = cache[pkg.name]
            if pkg.name == 'elbe-bootstrap':
                pkgver = p.versions[0]
            else:
                pkgver = p.installed

            dsc = pkgver.fetch_source(
                '/var/cache/elbe/sources',
                ElbeAcquireProgress(
                    cb=None),
                unpack=False)
            repo.includedsc(dsc)
        except ValueError:
            log.printo("No sources for Package " + pkg.name +
                       "-" + str(pkg.installed_version))
        except FetchError:
            log.printo(
                "Source for Package " +
                pkg.name +
                "-" +
                pkgver.version +
                " could not be downloaded")

    repo.finalize()

    return repo.buildiso(os.path.join(target, "src-cdrom.iso"))


def mk_binary_cdrom(
        rfs,
        arch,
        codename,
        init_codename,
        xml,
        target,
        log,
        cdrom_size=CDROM_SIZE):

    rfs.mkdir_p('/var/cache/elbe/binaries/added')
    rfs.mkdir_p('/var/cache/elbe/binaries/main')
    hostfs.mkdir_p('/var/cache/elbe/binaries/main')

    if xml is not None:
        mirror = xml.get_primary_mirror(rfs.fname("cdrom"))
    else:
        mirror = 'http://ftp.de.debian.org/debian'

    repo_path = os.path.join(target, "binrepo")
    target_repo_path = os.path.join(repo_path, 'targetrepo')

    repo = CdromInitRepo(arch, init_codename,
                         repo_path, log, cdrom_size, mirror)

    target_repo = CdromBinRepo(arch, codename, None,
                               target_repo_path, log, cdrom_size, mirror)

    if xml is not None:
        pkglist = get_initvm_pkglist()
        cache = Cache()
        cache.open()
        for pkg in pkglist:
            try:
                p = cache[pkg.name]
                if pkg.name == 'elbe-bootstrap':
                    pkgver = p.versions[0]
                else:
                    pkgver = p.installed
                deb = pkgver.fetch_binary('/var/cache/elbe/binaries/main',
                                          ElbeAcquireProgress(cb=None))
                repo.includedeb(deb, 'main')
            except ValueError:
                log.printo("No Package " + pkg.name +
                           "-" + str(pkg.installed_version))
            except FetchError:
                log.printo(
                    "Package " +
                    pkg.name +
                    "-" +
                    pkgver.version +
                    " could not be downloaded")
            except TypeError:
                log.printo("Package " +
                           pkg.name +
                           "-" +
                           str(pkg.installed_version) +
                           " missing name or version")

        cache = get_rpcaptcache(rfs, "aptcache.log", arch)
        for p in xml.node("debootstrappkgs"):
            pkg = XMLPackage(p, arch)
            try:
                deb = cache.download_binary(pkg.name,
                                            '/var/cache/elbe/binaries/main',
                                            pkg.installed_version)
                target_repo.includedeb(deb, 'main')
            except ValueError:
                log.printo(
                    "No Package " +
                    pkg.name +
                    "-" +
                    pkg.installed_version)
            except FetchError:
                log.printo(
                    "Package " +
                    pkg.name +
                    "-" +
                    pkg.installed_version +
                    " could not be downloaded")
            except TypeError:
                log.printo(
                    "Package " +
                    pkg.name +
                    "-" +
                    pkg.installed_version +
                    " missing name or version")

    cache = get_rpcaptcache(rfs, "aptcache.log", arch)
    pkglist = cache.get_installed_pkgs()
    for pkg in pkglist:
        try:
            deb = cache.download_binary(pkg.name,
                                        '/var/cache/elbe/binaries/added',
                                        pkg.installed_version)
            target_repo.includedeb(deb, 'added', pkg.name, True)
        except KeyError as ke:
            log.printo(str(ke))
        except ValueError:
            log.printo("No Package " + pkg.name + "-" + pkg.installed_version)
        except FetchError:
            log.printo("Package " +
                       pkg.name +
                       "-" +
                       str(pkg.installed_version) +
                       " could not be downloaded")
        except TypeError:
            log.printo(
                "Package " +
                pkg.name +
                "-" +
                pkg.installed_version +
                " missing name or version")

    repo.finalize()
    target_repo.finalize()

    # Mark the binary repo with the necessary Files
    # to make the installer accept this as a CDRom
    repo_fs = Filesystem(repo_path)
    repo_fs.mkdir_p(".disk")
    repo_fs.write_file(".disk/base_installable", 0o644, "main\n")
    repo_fs.write_file(".disk/base_components", 0o644, "main\n")
    repo_fs.write_file(".disk/cd_type", 0o644, "not_complete\n")
    repo_fs.write_file(".disk/info", 0o644, "elbe inst cdrom - full cd\n")
    repo_fs.symlink(".", "debian", allow_exists=True)
    repo_fs.write_file("md5sum.txt", 0o644, "")

    # write source xml onto cdrom
    xml.xml.write(repo_fs.fname('source.xml'))

    target_repo_fs = Filesystem(target_repo_path)
    target_repo_fs.write_file(".aptignr", 0o644, "")

    return repo.buildiso(os.path.join(target, "bin-cdrom.iso"))
