# ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (c) 2014-2016 Torben Hohn <torben.hohn@linutronix.de>
# Copyright (c) 2014-2015, 2017 Manuel Traut <manut@linutronix.de>
# Copyright (c) 2016 John Ogness <john.ogness@linutronix.de>
# Copyright (c) 2017 Philipp Arras <philipp.arras@linutronix.de>
#
# SPDX-License-Identifier: GPL-3.0-or-later

import os
import logging

from shutil import copyfile

from apt.package import FetchError

from elbepack.archivedir import archive_tmpfile
from elbepack.rpcaptcache import get_rpcaptcache
from elbepack.repomanager import CdromSrcRepo
from elbepack.repomanager import CdromBinRepo
from elbepack.repomanager import CdromInitRepo
from elbepack.aptpkgutils import XMLPackage
from elbepack.filesystem import Filesystem, hostfs
from elbepack.shellhelper import CommandError, do
from elbepack.isooptions import get_iso_options

CDROM_SIZE = 640 * 1000 * 1000

# pylint: disable=too-many-arguments
def add_source_pkg(repo, component, cache, pkg, version, forbid):
    if pkg in forbid:
        return
    pkg_id = "%s-%s" % (pkg, version)
    try:
        dsc = cache.download_source(pkg,
                                    '/var/cache/elbe/sources',
                                    version=version)
        repo.includedsc(dsc, component=component, force=True)
    except ValueError:
        logging.error("No sources for package '%s'", pkg_id)
    except FetchError:
        logging.error("Source for package '%s' could not be downloaded", pkg_id)

def mk_source_cdrom(components, codename,
                    init_codename, target,
                    cdrom_size=CDROM_SIZE, xml=None,
                    mirror='http://ftp.de.debian.org/debian'):

    # pylint: disable=too-many-arguments
    # pylint: disable=too-many-locals
    # pylint: disable=too-many-branches

    hostfs.mkdir_p('/var/cache/elbe/sources')

    repo = CdromSrcRepo(codename, init_codename,
                        os.path.join(target, "srcrepo"),
                        cdrom_size,
                        mirror)

    forbiddenPackages = []
    if xml is not None and xml.has('target/pkg-list'):
        for i in xml.node('target/pkg-list'):
            try:
                if i.tag == 'pkg' and i.et.attrib['on_src_cd'] == 'False':
                    forbiddenPackages.append(i.text('.').strip())
            except KeyError:
                pass

    for component, (rfs, cache, pkg_lst) in components.items():
        rfs.mkdir_p('/var/cache/elbe/sources')
        for pkg, version in pkg_lst:
            add_source_pkg(repo, component,
                           cache, pkg, version,
                           forbiddenPackages)

    # elbe fetch_initvm_pkgs has downloaded all sources to
    # /var/cache/elbe/sources
    # use walk_files to scan it, and add all dsc files.
    #
    # we can not just copy the source repo, like we do
    # with the bin repo, because the src cdrom can be split
    # into multiple cdroms

    initvm_repo = Filesystem('/var/cache/elbe/sources')

    for _ , dsc_real in initvm_repo.walk_files():
        if not dsc_real.endswith('.dsc'):
            continue

        repo.include_init_dsc(dsc_real, 'initvm')

    repo.finalize()

    if xml is not None:
        options = get_iso_options(xml)

        for arch_vol in xml.all('src-cdrom/archive'):
            volume_attr = arch_vol.et.get('volume')

            if volume_attr == 'all':
                volume_list = repo.volume_indexes
            else:
                volume_list = [int(v) for v in volume_attr.split(",")]
            for volume_number in volume_list:
                with archive_tmpfile(arch_vol.text(".")) as fp:
                    if volume_number in repo.volume_indexes:
                        do('tar xvfj "%s" -h -C "%s"' % (fp.name,
                                                         repo.get_volume_fs(volume_number).path))
                    else:
                        logging.warning("The src-cdrom archive's volume value "
                                        "is not contained in the actual volumes")
    else:
        options = ""

    return repo.buildiso(os.path.join(target, "src-cdrom.iso"), options=options)

def mk_binary_cdrom(rfs, arch, codename, init_codename, xml, target):
    # pylint: disable=too-many-arguments
    # pylint: disable=too-many-locals
    # pylint: disable=too-many-branches
    # pylint: disable=too-many-statements

    rfs.mkdir_p('/var/cache/elbe/binaries/added')
    rfs.mkdir_p('/var/cache/elbe/binaries/main')

    if xml is not None:
        mirror = xml.get_primary_mirror(rfs.fname("cdrom"))
    else:
        mirror = 'http://ftp.de.debian.org/debian'

    repo_path = os.path.join(target, "binrepo")
    target_repo_path = os.path.join(repo_path, 'targetrepo')

    # initvm repo has been built upon initvm creation
    # just copy it. the repo __init__() afterwards will
    # not touch the repo config, nor generate a new key.
    try:
        do('cp -av /var/cache/elbe/initvm-bin-repo "%s"' % repo_path)
    except CommandError:
        # When /var/cache/elbe/initvm-bin-repo has not been created
        # (because the initvm install was an old version or somthing,
        #  log an error, and continue with an empty directory.
        logging.exception("/var/cache/elbe/initvm-bin-repo does not exist\n"
                          "The generated CDROM will not contain initvm pkgs\n"
                          "This happened because the initvm was probably\n"
                          "generated with --skip-build-bin")

        do('mkdir -p "%s"' % repo_path)

    repo = CdromInitRepo(init_codename, repo_path, mirror)

    target_repo = CdromBinRepo(arch, codename, None,
                               target_repo_path, mirror)

    if xml is not None:
        cache = get_rpcaptcache(rfs, arch)
        for p in xml.node("debootstrappkgs"):
            pkg = XMLPackage(p, arch)
            pkg_id = "%s-%s" % (pkg.name, pkg.installed_version)
            try:
                deb = cache.download_binary(pkg.name,
                                            '/var/cache/elbe/binaries/main',
                                            pkg.installed_version)
                target_repo.includedeb(deb, 'main')
            except ValueError:
                logging.error("No package '%s'", pkg_id)
            except FetchError:
                logging.error("Package '%s' could not be downloaded", pkg_id)
            except TypeError:
                logging.error("Package '%s' missing name or version", pkg_id)

    cache = get_rpcaptcache(rfs, arch)
    pkglist = cache.get_installed_pkgs()
    for pkg in pkglist:
        pkg_id = "%s-%s" % (pkg.name, pkg.installed_version)
        try:
            deb = cache.download_binary(pkg.name,
                                        '/var/cache/elbe/binaries/added',
                                        pkg.installed_version)
            target_repo.includedeb(deb, 'added', pkg.name, True)
        except KeyError as ke:
            logging.error(str(ke))
        except ValueError:
            logging.error("No package '%s'", pkg_id)
        except FetchError:
            logging.error("Package '%s' could not be downloaded", pkg_id)
        except TypeError:
            logging.error("Package '%s' missing name or version", pkg_id)

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

    # copy initvm-cdrom.gz and vmlinuz
    copyfile('/var/cache/elbe/installer/initrd-cdrom.gz',
             repo_fs.fname('initrd-cdrom.gz'))
    copyfile('/var/cache/elbe/installer/vmlinuz',
             repo_fs.fname('vmlinuz'))

    target_repo_fs = Filesystem(target_repo_path)
    target_repo_fs.write_file(".aptignr", 0o644, "")

    return repo.buildiso(os.path.join(target, "bin-cdrom.iso"))
