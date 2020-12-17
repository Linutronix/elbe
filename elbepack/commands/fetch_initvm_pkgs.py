# ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (c) 2018 Torben Hohn <torbenh@linutronix.de>
# Copyright (c) 2018 Manuel Traut <manut@linutronix.de>
#
# SPDX-License-Identifier: GPL-3.0-or-later

import sys
import logging
from optparse import OptionParser

from apt.package import FetchError
from apt import Cache

from elbepack.elbexml import ElbeXML, ValidationError
from elbepack.repomanager import CdromInitRepo, CdromSrcRepo
from elbepack.dump import get_initvm_pkglist
from elbepack.aptprogress import ElbeAcquireProgress
from elbepack.filesystem import hostfs
from elbepack.log import elbe_logging
from elbepack.shellhelper import do
from elbepack.aptpkgutils import fetch_binary


def run_command(argv):

    # TODO - Set threshold and remove pylint directives
    #
    # We might want to make the threshold higher for certain
    # files/directories or just globaly.

    # pylint: disable=too-many-locals
    # pylint: disable=too-many-branches
    # pylint: disable=too-many-statements

    oparser = OptionParser(
        usage="usage: %prog fetch_initvm_pkgs [options] <xmlfile>")

    oparser.add_option("-b", "--binrepo", dest="binrepo",
                       default="/var/cache/elbe/initvm-bin-repo",
                       help="directory where the bin repo should reside")

    oparser.add_option("-s", "--srcrepo", dest="srcrepo",
                       default="/var/cache/elbe/initvm-src-repo",
                       help="directory where the src repo should reside")

    oparser.add_option("--skip-validation", action="store_true",
                       dest="skip_validation", default=False,
                       help="Skip xml schema validation")

    oparser.add_option("--cdrom-mount-path", dest="cdrom_path",
                       help="path where cdrom is mounted")

    oparser.add_option("--cdrom-device", dest="cdrom_device",
                       help="cdrom device, in case it has to be mounted")

    oparser.add_option("--apt-archive", dest="archive",
                       default="/var/cache/elbe/binaries/main",
                       help="path where binary packages are downloaded to.")

    oparser.add_option("--src-archive", dest="srcarchive",
                       default="/var/cache/elbe/sources",
                       help="path where src packages are downloaded to.")

    oparser.add_option("--skip-build-sources", action="store_false",
                       dest="build_sources", default=True,
                       help="Skip downloading Source Packages")

    oparser.add_option("--skip-build-bin", action="store_false",
                       dest="build_bin", default=True,
                       help="Skip downloading binary packages")

    (opt, args) = oparser.parse_args(argv)

    if len(args) != 1:
        print("wrong number of arguments")
        oparser.print_help()
        sys.exit(20)

    try:
        xml = ElbeXML(args[0], skip_validate=opt.skip_validation)
    except ValidationError as e:
        print(str(e))
        print("xml validation failed. Bailing out")
        sys.exit(20)

    with elbe_logging({"streams":sys.stdout}):

        if opt.cdrom_path:
            if opt.cdrom_device:
                do('mount "%s" "%s"' % (opt.cdrom_device, opt.cdrom_path))

            # a cdrom build is identified by the cdrom option
            # the xml file that is copied into the initvm
            # by the initrd does not have the cdrom tags setup.
            mirror = "file://%s" % opt.cdrom_path
        else:
            mirror = xml.get_initvm_primary_mirror(opt.cdrom_path)

        init_codename = xml.get_initvm_codename()

        # Binary Repo
        #
        repo = CdromInitRepo(init_codename, opt.binrepo, mirror)

        hostfs.mkdir_p(opt.archive)

        if opt.build_bin:
            pkglist = get_initvm_pkglist()
            cache = Cache()
            cache.open()
            for pkg in pkglist:
                pkg_id = "%s-%s" % (pkg.name, pkg.installed_version)
                try:
                    p = cache[pkg.name]
                    pkgver = p.installed
                    deb = fetch_binary(pkgver,
                                       opt.archive,
                                       ElbeAcquireProgress(cb=None))
                    repo.includedeb(deb, 'main', prio=pkgver.priority)
                except ValueError:
                    logging.exception('No package "%s"', pkg_id)
                except FetchError:
                    logging.exception('Package "%s-%s" could not be downloaded',
                                      pkg.name, pkgver.version)
                except TypeError:
                    logging.exception('Package "%s" missing name or version', pkg_id)

        repo.finalize()

        # Source Repo
        #
        repo = CdromSrcRepo(init_codename, init_codename, opt.srcrepo, 0, mirror)
        hostfs.mkdir_p(opt.srcarchive)

        # a cdrom build does not have sources
        # skip adding packages to the source repo
        #
        # FIXME: we need a way to add source cdroms later on
        if opt.cdrom_path:
            opt.build_sources = False

        if opt.build_sources:
            for pkg in pkglist:
                pkg_id = "%s-%s" % (pkg.name, pkg.installed_version)
                try:
                    p = cache[pkg.name]
                    pkgver = p.installed
                    dsc = pkgver.fetch_source(opt.srcarchive,
                                              ElbeAcquireProgress(cb=None),
                                              unpack=False)
                    repo.include_init_dsc(dsc, 'initvm')
                except ValueError:
                    logging.exception('No package "%s"', pkg_id)
                except FetchError:
                    logging.exception('Package "%s-%s" could not be downloaded', pkg.name, pkgver.version)
                except TypeError:
                    logging.exception('Package "%s" missing name or version', pkg_id)

        repo.finalize()

        if opt.cdrom_device:
            do('umount "%s"' % opt.cdrom_device)
