# ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (c) 2013-2014 Torben Hohn <torbenh@linutronix.de>
# Copyright (c) 2014, 2017 Manuel Traut <manut@linutronix.de>
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import print_function

import logging
import sys
from optparse import OptionParser

import apt
import apt.progress

from elbepack.treeutils import etree
from elbepack.log import elbe_logging


def set_pkgs(pkglist):

    cache = apt.Cache()
    cache.update()
    cache.open(None)

    errors = 0

    with cache.actiongroup():

        for p in cache:
            if not p.is_installed:
                continue
            if p.essential or \
               p.is_auto_installed or \
               p.name in pkglist or \
               p.installed.priority == "important" or \
               p.installed.priority == "required":
                continue
            logging.info("MARK REMOVE %s", p.name)
            p.mark_delete(auto_fix=False, purge=True)

        for name in pkglist:

            if name not in cache:
                logging.warning('Package "%s" does not exist', name)
                errors += 1
                continue

            cp = cache[name]

            cp.mark_install()
            logging.info("MARK INSTALL %s", cp.name)

        cache.commit(apt.progress.base.AcquireProgress(),
                     apt.progress.base.InstallProgress())

        cache.update()
        cache.open(None)

        for p in cache:
            if not p.is_installed:
                continue
            if p.is_auto_removable:
                p.mark_delete(purge=True)
                logging.info("MARKED AS AUTOREMOVE %s", p.name)

    cache.commit(apt.progress.base.AcquireProgress(),
                 apt.progress.base.InstallProgress())

    return errors


def run_command(argv):
    oparser = OptionParser(usage="usage: %prog adjustpkgs [options] <xmlfile>")

    oparser.add_option("-o", "--output", dest="output",
                       help="name of logfile")
    oparser.add_option("-n", "--name", dest="name",
                       help="name of the project (included in the report)")
    (opt, args) = oparser.parse_args(argv)

    if len(args) != 1:
        print("Wrong number of arguments")
        oparser.print_help()
        sys.exit(20)

    if not opt.output:
        return 0

    xml = etree(args[0])
    xml_pkglist = xml.node("/target/pkg-list")
    xml_pkgs = [p.et.text for p in xml_pkglist]

    # TODO: install buildimage packages after target image generation
    #         and remove theme before target image generation
    #         we need to introduce additional arguments for this
    #       in default copy mode chroot to the target and remove elbe-daemon
    #         and its dependencies (if it is not in  target/pkg-list.
    buildenv_pkgs = ["python3-elbe-buildenv"]
    if xml.has("./project/buildimage/pkg-list"):
        buildenv_pkgs.extend([p.et.text for p in xml.node(
            "project/buildimage/pkg-list")])


    with elbe_logging({"files":opt.output}):
        logging.info("ELBE Report for Project %s", opt.name)
        return set_pkgs(xml_pkgs + buildenv_pkgs)


if __name__ == "__main__":
    run_command(sys.argv[1:])
