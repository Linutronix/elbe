# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2018 Linutronix GmbH

import argparse
import contextlib
import logging
import os
import subprocess
import sys

from apt import Cache
from apt.package import FetchError

from elbepack.aptpkgutils import fetch_source, get_corresponding_source_packages
from elbepack.aptprogress import ElbeAcquireProgress
from elbepack.dump import get_initvm_pkglist
from elbepack.elbexml import ElbeXML, ValidationError
from elbepack.imgutils import mount
from elbepack.log import elbe_logging
from elbepack.repomanager import CdromInitRepo, CdromSrcRepo


def run_command(argv):

    aparser = argparse.ArgumentParser(prog='elbe fetch_initvm_pkgs')

    aparser.add_argument('-b', '--binrepo', dest='binrepo',
                         default='/var/cache/elbe/initvm-bin-repo',
                         help='directory where the bin repo should reside')

    aparser.add_argument('-s', '--srcrepo', dest='srcrepo',
                         default='/var/cache/elbe/initvm-src-repo',
                         help='directory where the src repo should reside')

    aparser.add_argument('--skip-validation', action='store_true',
                         dest='skip_validation', default=False,
                         help='Skip xml schema validation')

    aparser.add_argument('--cdrom-mount-path', dest='cdrom_path',
                         help='path where cdrom is mounted')

    aparser.add_argument('--cdrom-device', dest='cdrom_device',
                         help='cdrom device, in case it has to be mounted')

    aparser.add_argument('--apt-archive', dest='archive',
                         default='/var/cache/elbe/binaries/main',
                         help='path where binary packages are downloaded to.')

    aparser.add_argument('--src-archive', dest='srcarchive',
                         default='/var/cache/elbe/sources',
                         help='path where src packages are downloaded to.')

    aparser.add_argument('--skip-build-sources', action='store_false',
                         dest='build_sources', default=True,
                         help='Skip downloading Source Packages')

    aparser.add_argument('--skip-build-bin', action='store_false',
                         dest='build_bin', default=True,
                         help='Skip downloading binary packages')

    aparser.add_argument('xmlfile')

    args = aparser.parse_args(argv)

    try:
        xml = ElbeXML(args.xmlfile, skip_validate=args.skip_validation)
    except ValidationError as e:
        print(str(e))
        print('xml validation failed. Bailing out')
        sys.exit(47)

    with elbe_logging(streams=sys.stdout), contextlib.ExitStack() as stack:

        if args.cdrom_path:
            if args.cdrom_device:
                stack.enter_context(mount(args.cdrom_device, args.cdrom_path))

            # a cdrom build is identified by the cdrom option
            # the xml file that is copied into the initvm
            # by the initrd does not have the cdrom tags setup.
            mirror = f'file://{args.cdrom_path}'
        else:
            mirror = xml.get_initvm_primary_mirror(args.cdrom_path)

        init_codename = xml.get_initvm_codename()

        # Binary Repo
        #
        repo = CdromInitRepo(init_codename, args.binrepo, mirror)

        os.makedirs(args.archive, exist_ok=True)

        if args.build_bin:
            pkglist = get_initvm_pkglist()
            cache = Cache()
            cache.open()
            for pkg in pkglist:
                pkg_id = f'{pkg.name}-{pkg.installed_version}'
                retry = 1
                while retry < 3:
                    try:
                        p = cache[pkg.name]
                        pkgver = p.installed
                        deb = pkgver.fetch_binary(args.archive, ElbeAcquireProgress(cb=None))
                        repo.includedeb(deb, 'main', prio=pkgver.priority)
                        break
                    except ValueError:
                        logging.exception('No package "%s"', pkg_id)
                        retry = 3
                    except FetchError:
                        logging.exception('Package "%s-%s" could not be downloaded',
                                          pkg.name, pkgver.version)
                        retry += 1
                    except TypeError:
                        logging.exception('Package "%s" missing name or version',
                                          pkg_id)
                        retry = 3
                    except subprocess.CalledProcessError:
                        logging.exception('Package "%s-%s" could not be added to repo.',
                                          pkg.name, pkgver.version)
                        retry += 1
                    if retry >= 3:
                        logging.error('Failed to get binary Package "%s"',
                                      pkg_id)

        repo.finalize()

        # Source Repo
        #
        repo = CdromSrcRepo(init_codename, init_codename, args.srcrepo, 0, mirror)
        os.makedirs(args.srcarchive, exist_ok=True)

        # a cdrom build does not have sources
        # skip adding packages to the source repo
        #
        # FIXME: we need a way to add source cdroms later on
        if args.cdrom_path:
            args.build_sources = False

        if args.build_sources:
            srcpkglist = get_corresponding_source_packages(cache, [pkg.name for pkg in pkglist])
            for name, version in srcpkglist:
                pkg_id = f'{name}-{version}'
                retry = 1
                while retry < 3:
                    try:
                        dsc = fetch_source(name, version, args.srcarchive,
                                           ElbeAcquireProgress())
                        repo.include_init_dsc(dsc, 'initvm')
                        break
                    except ValueError:
                        logging.exception('No package "%s"', pkg_id)
                        retry = 3
                    except FetchError:
                        logging.exception('Package "%s" could not be downloaded',
                                          pkg_id)
                        retry += 1
                    except TypeError:
                        logging.exception('Package "%s" missing name or version',
                                          pkg_id)
                        retry = 3
                    except subprocess.CalledProcessError:
                        logging.exception('Package "%s" could not be added to repo.',
                                          pkg_id)
                        retry += 1
                    if retry >= 3:
                        logging.error('Failed to get source Package "%s"',
                                      pkg_id)

        repo.finalize()
