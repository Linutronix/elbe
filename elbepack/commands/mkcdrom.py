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


from optparse import OptionParser
import datetime
import sys
import os

from elbepack.elbexml import ElbeXML, ValidationError
from elbepack.asciidoclog import StdoutLog, ASCIIDocLog
from elbepack.rfs import BuildEnv
from elbepack.filesystem import ChRootFilesystem
from elbepack.shellhelper import system

from elbepack.cdroms import mk_source_cdrom, mk_binary_cdrom



def run_command( argv ):
    oparser = OptionParser(usage="usage: %prog mkcdrom [options] <builddir>")
    oparser.add_option( "--skip-validation", action="store_true",
                        dest="skip_validation", default=False,
                        help="Skip xml schema validation" )
    oparser.add_option( "--buildtype", dest="buildtype",
                        help="Override the buildtype" )
    oparser.add_option( "--arch", dest="arch",
                        help="Override the architecture" )
    oparser.add_option( "--codename", dest="codename",
                        help="Override the codename" )
    oparser.add_option( "--rfs-only", action="store_true",
                        dest="rfs_only", default=False,
                        help="builddir points to RFS" )
    oparser.add_option( "--log", dest="log",
                        help="Log to filename" )
    oparser.add_option( "--binary", action="store_true",
                        dest="binary", default=False,
                        help="build binary cdrom" )
    oparser.add_option( "--source", action="store_true",
                        dest="source", default=False,
                        help="build source cdrom" )

    (opt,args) = oparser.parse_args(argv)

    if len(args) != 1:
        print "wrong number of arguments"
        oparser.print_help()
        sys.exit(20)

    if opt.log:
        log = ASCIIDocLog( opt.log )
    else:
        log = StdoutLog()

    if not opt.rfs_only:
        builddir = os.path.abspath(args[0])
        sourcexml = os.path.join( builddir, "source.xml" )
        chroot = os.path.join( builddir, "chroot" )

        if opt.buildtype:
            buildtype = opt.buildtype
        else:
            buildtype = None

        try:
            xml = ElbeXML( sourcexml, buildtype=buildtype, skip_validate=opt.skip_validation )
        except ValidationError:
            print "xml validation failed. Bailing out"
            sys.exit(20)

        buildenv = BuildEnv(xml, log, chroot)
        rfs = buildenv.rfs
        arch = xml.text("project/arch", key="arch" )
        codename = xml.text("project/suite" )
    else:
        builddir = os.path.abspath( os.path.curdir )
        rfs = ChRootFilesystem( args[0] )
        arch = opt.arch
        codename = opt.codename
        xml = None

    if opt.source:
        mk_source_cdrom( rfs, arch, codename, builddir, log )

    if opt.binary:
        mk_binary_cdrom( rfs, arch, codename, xml, builddir, log )
