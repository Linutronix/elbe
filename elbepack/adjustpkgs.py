#!/usr/bin/env python
#
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

from treeutils import etree
from optparse import OptionParser
from subprocess import Popen, PIPE, STDOUT
import datetime
import apt
import apt.progress

import sys
import os

class asccidoclog(object):
    def __init__(self, fname):
        if os.path.isfile(fname):
            os.unlink(fname)
        self.fp = file(fname, "w")

    def printo(self, text=""):
        self.fp.write(text+"\n")

    def print_raw(self, text):
        self.fp.write(text)

    def h1(self, text):
        self.printo()
        self.printo(text)
        self.printo("="*len(text))
        self.printo()

    def h2(self, text):
        self.printo()
        self.printo(text)
        self.printo("-"*len(text))
        self.printo()

    def table(self):
        self.printo( "|=====================================" )

    def verbatim_start(self):
        self.printo( "------------------------------------------------------------------------------" )

    def verbatim_end(self):
        self.printo( "------------------------------------------------------------------------------" )
        self.printo()


def run_command( argv ):
    oparser = OptionParser(usage="usage: %prog adjustpkgs [options] <xmlfile>")

    oparser.add_option( "-o", "--output", dest="output",
                        help="name of logfile" )
    oparser.add_option( "-n", "--name", dest="name",
                        help="name of the project (included in the report)" )
    (opt,args) = oparser.parse_args(argv)

    if len(args) != 1:
       print "Wrong number of arguments"
       oparser.print_help()
       sys.exit(20)

    if not opt.output:
        return 0

    outf = asccidoclog(opt.output)

    if opt.name:
        outf.h1( "ELBE Report for Project "+opt.name )
    else:
        outf.h1( "ELBE Report" )

    xml = etree( args[0] )

    pkgs = xml.node("/target/pkg-list")

    cache = apt.Cache()
    cache.update()
    cache.open(None)

    errors = 0

    pkglist = ["elbe-daemon"]

    if xml.has("target/images/msdoshd/grub-install"):
        pkglist = ["elbe-daemon", "grub-pc"]

    if xml.has("./project/buildimage/pkg-list"):
        build_pkglist = [p.et.text for p in xml.node("project/buildimage/pkg-list")]
    else:
        build_pkglist = []
    with cache.actiongroup():

        want_pkgs = [p.et.text for p in pkgs] + pkglist + build_pkglist

        for p in cache:
            if not p.is_installed:
                continue
            if p.essential or p.is_auto_installed or (p.name in want_pkgs) or p.installed.priority == "important" or p.installed.priority == "required":
                continue
            p.mark_auto()

        for name in want_pkgs:

            if not name in cache:
                outf.printo( "- package %s does not exist" % name )
                errors += 1
                continue

            cp = cache[name]

            cp.mark_install()

        for p in cache:
            if not p.is_installed:
                continue
            if p.is_auto_removable:
                p.mark_delete( purge=True )

    cache.commit(apt.progress.base.AcquireProgress(),
                 apt.progress.base.InstallProgress())

if __name__ == "__main__":
    run_command( sys.argv[1:] )
