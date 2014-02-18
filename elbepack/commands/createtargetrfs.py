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
#

import sys
import os
import time
import shutil
import subprocess
from optparse import OptionParser

import elbepack
from elbepack.treeutils import etree
from elbepack.validate import validate_xml
from elbepack.xmldefaults import ElbeDefaults
from elbepack.version import elbe_version

from elbepack.elbexml import ElbeXML
from elbepack.filesystem import Filesystem

from elbepack.filesystem import extract_target, dump_elbeversion, do_elbe_dump
from elbepack.filesystem import create_licenses, part_target, extract_some_files

def run_command(argv):

    oparser = OptionParser(usage="usage: %prog create-target-rfs [options] <xmlfile>")
    oparser.add_option( "-t", "--target", dest="target",
                         help="directoryname of target" )
    oparser.add_option( "-d", "--debug", dest="debug", default=False,
                         help="additional debug output" )
    oparser.add_option( "-b", "--buildchroot", dest="buildchroot", default=False, action = 'store_true',
                         help="copy kernel to /opt/elbe" )
    oparser.add_option( "-o", "--output", dest="output",
                         help="name of logfile" )
    oparser.add_option( "-r", "--rootdir", dest="rootdir", default = "/",
                         help="name of the root directory")
    oparser.add_option("--buildtype", dest="buildtype",
            help="Override the buildtype" )

    (opt, args) = oparser.parse_args(argv)
    if len(args) != 1:
        print "wrong number of arguments"
        oparser.print_help()
        sys.exit(1)

    if not opt.target:
        print "Missing target (-t)"
        oparser.print_help()
        sys.exit(1)

    try:
        xml = ElbeXML( args[0], buildtype=opt.buildtype )
    except ValidationError:
        print "xml validation failed. Bailing out"
        sys.exit(20)

    rootfs = Filesystem(opt.rootdir)
    targetfs = Filesystem(opt.target, clean=True)

    os.chdir(rootfs.fname(''))

    extract_target( rootfs, xml, dst )
    dump_elbeversion(xml, dst)
    do_elbe_dump(xml, dst)
    create_licenses(rootfs, dst)
    part_target(xml,dst)
    extract_some_files(xml, opt.debug, opt.buildchroot)

if __name__ == "__main__":
    run_command(sys.argv[1:])
