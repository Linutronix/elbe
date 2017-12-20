# ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (C) 2013  Linutronix GmbH
#
# This file is part of ELBE.
#
# ELBE is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# ELBE is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with ELBE.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import print_function

import os
import sys

import apt
import apt_pkg

from optparse import OptionParser

from elbepack.elbexml import ElbeXML, ValidationMode


def run_command(argv):

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
            if p.current_ver and not gc[p.name].is_auto_installed and not p.essential:
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
            if p.current_ver and not fc[p.name].is_auto_installed and not p.essential:
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
