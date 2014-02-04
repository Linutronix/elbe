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

class adjpkg(object):
    def __init__(self, logfile, name):

        self.outf = asccidoclog(logfile)

        if name:
            self.outf.h1( "ELBE Report for Project "+name )
        else:
            self.outf.h1( "ELBE Report" )

    def set_pkgs(self, pkglist):

        cache = apt.Cache()
        cache.update()
        cache.open(None)

        errors = 0

        with cache.actiongroup():

            for p in cache:
                if not p.is_installed:
                    continue
                if p.essential or p.is_auto_installed or (p.name in pkglist) or p.installed.priority == "important" or p.installed.priority == "required":
                    continue
                print "MARK REMOVE %s" % p.name
                p.mark_delete( auto_fix=False, purge=True )

            for name in pkglist:

                if not name in cache:
                    self.outf.printo( "- package %s does not exist" % name )
                    errors += 1
                    continue

                cp = cache[name]

                cp.mark_install()
                print "MARK INSTALL %s" % cp.name

            cache.commit(apt.progress.base.AcquireProgress(),
                         apt.progress.base.InstallProgress())


            cache.update()
            cache.open(None)

            for p in cache:
                if not p.is_installed:
                    continue
                if p.is_auto_removable:
                    p.mark_delete( purge=True )
                    print "MARKED AS AUTOREMOVE %s" % p.name

        cache.commit(apt.progress.base.AcquireProgress(),
                     apt.progress.base.InstallProgress())

        return errors

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


    xml = etree( args[0] )

    pkgs = xml.node("/target/pkg-list")

    cache = apt.Cache()
    cache.update()
    cache.open(None)

    errors = 0

    pkglist = ["elbe-daemon"]

    if xml.has("/target/images/msdoshd/grub-install"):
        pkglist = ["elbe-daemon", "grub-pc"]

    if xml.has("./project/buildimage/pkg-list"):
        buildenv_pkgs = [p.et.text for p in xml.node("project/buildimage/pkg-list")]

    adj = adjpkg(opt.output, opt.name)
    return adj.set_pkgs(xml_pkgs + mandatory_pkgs + buildenv_pkgs)

if __name__ == "__main__":
    run_command( sys.argv[1:] )
