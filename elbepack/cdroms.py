# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2014-2017 Linutronix GmbH

import logging
import os
import pathlib
import subprocess
from shutil import copyfile

from apt.package import FetchError

from elbepack.aptpkgutils import XMLPackage
from elbepack.archivedir import archive_tmpfile
from elbepack.isooptions import get_iso_options
from elbepack.repomanager import CdromBinRepo, CdromInitRepo, CdromSrcRepo
from elbepack.rpcaptcache import get_rpcaptcache
from elbepack.shellhelper import do

CDROM_SIZE = 640 * 1000 * 1000


def add_source_pkg(repo, component, cache, pkg, version, forbid):
    if pkg in forbid:
        logging.info("Ignoring source package %s", pkg)
        return
    pkg_id = f'{pkg}-{version}'
    try:
        dsc = cache.download_source(pkg,
                                    version,
                                    '/var/cache/elbe/sources')
        repo.includedsc(dsc, components=component, force=True)
    except ValueError as e:
        logging.error("No sources for package '%s': %s", pkg_id, str(e))
    except FetchError as e:
        logging.error("Source for package '%s' could not be downloaded: %s", pkg_id, str(e))


def mk_source_cdrom(components, codename,
                    init_codename, target,
                    cdrom_size=CDROM_SIZE, xml=None,
                    mirror='http://deb.debian.org/debian'):

    os.makedirs('/var/cache/elbe/sources', exist_ok=True)

    forbidden_packages = []
    if xml is not None and xml.has('target/pkg-list'):
        for i in xml.node('target/pkg-list'):
            try:
                if i.tag == 'pkg' and i.et.attrib['on_src_cd'] == 'False':
                    forbidden_packages.append(i.text('.').strip())
            except KeyError:
                pass

    repos = {}

    for component in components.keys():
        rfs, cache, pkg_lst = components[component]
        logging.info('Adding %s component', component)

        forbidden_src_packages = set()
        for name, _ in cache.get_corresponding_source_packages(forbidden_packages, include_built_using=False):
            forbidden_src_packages.add(name)

        rfs.mkdir_p('/var/cache/elbe/sources')
        repo = CdromSrcRepo(codename, init_codename,
                            os.path.join(target, f'srcrepo-{component}'),
                            cdrom_size, mirror)
        repos[component] = repo
        for pkg, version in pkg_lst:
            add_source_pkg(repo, component,
                           cache, pkg, version,
                           forbidden_src_packages)

        if component == 'main' and xml is not None:
            for p in xml.node('debootstrappkgs'):
                pkg = XMLPackage(p)
                srcpkgs = cache.get_corresponding_source_packages([pkg])
                for srcpkg, srcpkg_ver in srcpkgs:
                    add_source_pkg(repo, component, cache, srcpkg, srcpkg_ver, forbidden_src_packages)

    # elbe fetch_initvm_pkgs has downloaded all sources to
    # /var/cache/elbe/sources
    # use os.walk to scan it, and add all dsc files.
    #
    # we can not just copy the source repo, like we do
    # with the bin repo, because the src cdrom can be split
    # into multiple cdroms

    for dirpath, _, filenames in os.walk('/var/cache/elbe/sources'):
        for filename in filenames:
            if not filename.endswith('.dsc'):
                continue

            repos['main'].include_init_dsc(os.path.join(dirpath, filename), 'initvm')

    for repo in repos.values():
        repo.finalize()

    if xml is not None:
        options = get_iso_options(xml)

        for arch_vol in xml.all('src-cdrom/archive'):
            volume_attr = arch_vol.et.get('volume')

            for repo in repos.values():

                if volume_attr == 'all':
                    volume_list = repo.volume_indexes
                else:
                    volume_list = [int(v) for v in volume_attr.split(',')]
                for volume_number in volume_list:
                    with archive_tmpfile(arch_vol.text('.')) as fp:
                        if volume_number in repo.volume_indexes:
                            do(
                                f'tar xvfj "{fp.name}" -h -C '
                                f'"{repo.get_volume_path(volume_number)}"')
                        else:
                            logging.warning("The src-cdrom archive's volume value "
                                            'is not contained in the actual volumes')
    else:
        options = []

    return [(repo.buildiso(os.path.join(target, f'src-cdrom-{component}.iso'),
            options=options)) for component, repo in repos.items()]


def mk_binary_cdrom(rfs, arch, codename, init_codename, xml, target):

    rfs.mkdir_p('/var/cache/elbe/binaries/added')
    rfs.mkdir_p('/var/cache/elbe/binaries/main')

    if xml is not None:
        mirror = xml.get_primary_mirror(rfs.fname('cdrom'))
    else:
        mirror = 'http://deb.debian.org/debian'

    repo_path = pathlib.Path(target, 'binrepo')
    target_repo_path = repo_path / 'targetrepo'

    # initvm repo has been built upon initvm creation
    # just copy it. the repo __init__() afterwards will
    # not touch the repo config, nor generate a new key.
    try:
        do(f'cp -av /var/cache/elbe/initvm-bin-repo "{repo_path}"')
    except subprocess.CalledProcessError:
        # When /var/cache/elbe/initvm-bin-repo has not been created
        # (because the initvm install was an old version or somthing,
        #  log an error, and continue with an empty directory.
        logging.exception('/var/cache/elbe/initvm-bin-repo does not exist\n'
                          'The generated CDROM will not contain initvm pkgs\n'
                          'This happened because the initvm was probably\n'
                          'generated with --skip-build-bin')

        do(f'mkdir -p "{repo_path}"')

    repo = CdromInitRepo(init_codename, repo_path, mirror)

    target_repo = CdromBinRepo(arch, codename, None,
                               target_repo_path, mirror)

    if xml is not None:
        cache = get_rpcaptcache(rfs, arch)
        for p in xml.node('debootstrappkgs'):
            pkg = XMLPackage(p)
            pkg_id = f'{pkg.name}-{pkg.installed_version}'
            try:
                deb = cache.download_binary(pkg.name,
                                            '/var/cache/elbe/binaries/main',
                                            pkg.installed_version)
                target_repo.includedeb(deb, 'main', prio=pkg.installed_prio)
            except ValueError:
                logging.error("No package '%s'", pkg_id)
            except FetchError:
                logging.error("Package '%s' could not be downloaded", pkg_id)
            except TypeError:
                logging.error("Package '%s' missing name or version", pkg_id)

    cache = get_rpcaptcache(rfs, arch)
    pkglist = cache.get_installed_pkgs()
    for pkg in pkglist:
        pkg_id = f'{pkg.name}-{pkg.installed_version}'
        try:
            deb = cache.download_binary(pkg.name,
                                        '/var/cache/elbe/binaries/added',
                                        pkg.installed_version)
            target_repo.includedeb(deb, 'added', pkg.name, prio=pkg.installed_prio, force=True)
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
    dot_disk = repo_path / '.disk'
    dot_disk.mkdir()
    dot_disk.joinpath('base_installable').write_text('main\n')
    dot_disk.joinpath('base_components').write_text('main\n')
    dot_disk.joinpath('cd_type').write_text('not_complete\n')
    dot_disk.joinpath('info').write_text('elbe inst cdrom - full cd\n')

    repo_path.joinpath('debian').symlink_to(repo_path)
    repo_path.joinpath('md5sum.txt').touch()

    # write source xml onto cdrom
    xml.xml.write(repo_path / 'source.xml')

    # copy initvm-cdrom.gz and vmlinuz
    copyfile('/var/cache/elbe/installer/initrd-cdrom.gz',
             repo_path / 'initrd-cdrom.gz')
    copyfile('/var/cache/elbe/installer/vmlinuz',
             repo_path / 'vmlinuz')

    target_repo_path.joinpath('.aptignr').touch()

    return repo.buildiso(os.path.join(target, 'bin-cdrom.iso'))
