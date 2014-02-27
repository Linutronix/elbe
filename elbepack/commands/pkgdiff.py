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

import sys
import apt

from optparse import OptionParser


def run_command( argv ):

    oparser = OptionParser(usage="usage: %prog pkgdiff [options] <rfs1> <rfs2>")
    oparser.add_option( "--noauto", action="store_true", dest="noauto", default=False,
                        help="Dont compare automatically installed Packages" )
    (opt,args) = oparser.parse_args(argv)

    if len(args) != 2:
        print "Wrong number of arguments"
        oparser.print_help()
        sys.exit(20)

    gen_rfs = args[0]
    fix_rfs = args[1]

    gen_cache = apt.cache.Cache( rootdir=gen_rfs, memonly=True )
    fix_cache = apt.cache.Cache( rootdir=fix_rfs, memonly=True )

    gen_pkgs = {}
    for p in gen_cache:
        if opt.noauto:
            if p.is_installed and not p.is_auto_installed and not p.essential:
                gen_pkgs[p.name] = p.installed.version
        else:
            if p.is_installed and not p.essential:
                gen_pkgs[p.name] = p.installed.version

    fix_pkgs = {}
    for p in fix_cache:
        if opt.noauto:
            if p.is_installed and not p.is_auto_installed and not p.essential:
                fix_pkgs[p.name] = p.installed.version
        else:
            if p.is_installed and not p.essential:
                fix_pkgs[p.name] = p.installed.version

    for p in fix_pkgs.keys():
        if not p in gen_pkgs.keys():
            print "+<pkg>%s</pkg>" % p

    for p in gen_pkgs.keys():
        if not p in fix_pkgs.keys():
            print "-<pkg>%s</pkg>" % p

    for p in fix_pkgs.keys():
        if p in gen_pkgs.keys() and fix_pkgs[p] != gen_pkgs[p]:
            print "%s: Version mismatch %s != %s" % (p, fix_pkgs[p], gen_pkgs[p])


