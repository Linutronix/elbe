# ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (c) 2013, 2015, 2017 Manuel Traut <manut@linutronix.de>
# Copyright (c) 2014 Torben Hohn <torbenh@linutronix.de>
# Copyright (c) 2017 Philipp Arras <philipp.arras@linutronix.de>
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import print_function

import os
import sys

from optparse import OptionParser

import apt
import apt_pkg

from elbepack.elbexml import ElbeXML, ValidationMode


def run_command(argv):

    # pylint: disable=too-many-locals
    # pylint: disable=too-many-branches

    oparser = OptionParser(
        usage="usage: %prog pkgdiff [options] <rfs1> <rfs2>")
    oparser.add_option(
        "--noauto",
        action="store_true",
        dest="noauto",
        default=False,
        help="Dont compare automatically installed Packages")
    (opt, args) = oparser.parse_args(argv)

    if len(args) != 2:
        print("Wrong number of arguments")
        oparser.print_help()
        sys.exit(20)

    gen_rfs = args[0]
    fix_rfs = args[1]

    x = os.path.join(gen_rfs, 'etc/elbe_base.xml')
    xml = ElbeXML(
        x,
        skip_validate=True,
        url_validation=ValidationMode.NO_CHECK)
    arch = xml.text('project/arch', key='arch')

    apt_pkg.init_config()
    apt_pkg.config.set('RootDir', gen_rfs)
    apt_pkg.config.set('APT::Architecture', arch)
    apt_pkg.init_system()
    gen_cache = apt_pkg.Cache(apt.progress.base.OpProgress())
    gc = apt.Cache()

    gen_pkgs = {}
    for p in gen_cache.packages:
        if opt.noauto:
            if p.current_ver and not \
               gc[p.name].is_auto_installed and not \
               p.essential:
                gen_pkgs[p.name] = p.current_ver
        else:
            if p.current_ver and not p.essential:
                gen_pkgs[p.name] = p.current_ver

    apt_pkg.init_config()
    apt_pkg.config.set('RootDir', fix_rfs)
    apt_pkg.config.set('APT::Architecture', arch)
    apt_pkg.init_system()
    fix_cache = apt_pkg.Cache(apt.progress.base.OpProgress())
    fc = apt.Cache()

    fix_pkgs = {}
    for p in fix_cache.packages:
        if opt.noauto:
            if p.current_ver and not \
               fc[p.name].is_auto_installed and not \
               p.essential:
                fix_pkgs[p.name] = p.current_ver
        else:
            if p.current_ver and not p.essential:
                fix_pkgs[p.name] = p.current_ver

    for p in fix_pkgs:
        if p not in gen_pkgs:
            print("+<pkg>%s</pkg>" % p)

    for p in gen_pkgs.keys():
        if p not in fix_pkgs.keys():
            print("-<pkg>%s</pkg>" % p)

    for p in fix_pkgs.keys():
        if p in gen_pkgs.keys() and fix_pkgs[p] != gen_pkgs[p]:
            print(
                "%s: Version mismatch %s != %s" %
                (p, fix_pkgs[p], gen_pkgs[p]))
