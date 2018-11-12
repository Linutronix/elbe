# ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (c) 2018 Torben Hohn <torbenh@linutronix.de>
# Copyright (c) 2018 Manuel Traut <manut@linutronix.de>
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import print_function

import sys
from optparse import OptionParser

from apt.package import FetchError
from apt import Cache

from elbepack.elbexml import ElbeXML, ValidationError
from elbepack.repomanager import CdromInitRepo, CdromSrcRepo
from elbepack.asciidoclog import StdoutLog
from elbepack.dump import get_initvm_pkglist
from elbepack.aptprogress import ElbeAcquireProgress
from elbepack.filesystem import hostfs


def run_command(argv):
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

    oparser.add_option("--cdrom-mount-path", dest="cdrom",
                       help="path where cdrom is mounted")

    oparser.add_option("--apt-archive", dest="archive",
                       default="/var/cache/elbe/binaries/main",
                       help="path where binary packages are downloaded to.")

    oparser.add_option("--src-archive", dest="srcarchive",
                       default="/var/cache/elbe/sources",
                       help="path where src packages are downloaded to.")

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

    log = StdoutLog()
    mirror = xml.get_initvm_primary_mirror(opt.cdrom)
    init_codename = xml.get_initvm_codename()

    # Binary Repo
    #
    repo = CdromInitRepo(init_codename, opt.binrepo, log, 0, mirror)
    hostfs.mkdir_p(opt.archive)

    pkglist = get_initvm_pkglist()
    cache = Cache()
    cache.open()
    for pkg in pkglist:
        try:
            p = cache[pkg.name]
            pkgver = p.installed
            deb = pkgver.fetch_binary(opt.archive,
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

    repo.finalize()

    # Source Repo
    #
    repo = CdromSrcRepo(init_codename, init_codename, opt.srcrepo, log, 0, mirror)
    hostfs.mkdir_p(opt.srcarchive)

    for pkg in pkglist:
        try:
            p = cache[pkg.name]
            pkgver = p.installed
            dsc = pkgver.fetch_source(opt.srcarchive,
                                      ElbeAcquireProgress(cb=None),
                                      unpack=False)
            repo.include_init_dsc(dsc, 'initvm')
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

    repo.finalize()
