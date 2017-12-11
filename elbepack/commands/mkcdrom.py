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

from optparse import OptionParser
import sys
import os

from elbepack.elbeproject import ElbeProject
from elbepack.elbexml import ValidationError
from elbepack.asciidoclog import StdoutLog, ASCIIDocLog
from elbepack.efilesystem import ChRootFilesystem

from elbepack.cdroms import mk_source_cdrom, mk_binary_cdrom, CDROM_SIZE



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
    oparser.add_option( "--init_codename", dest="init_codename",
                        help="Override the initvm codename" )
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
    oparser.add_option( "--cdrom-size", action="store",
                        dest="cdrom_size", default=CDROM_SIZE, help="ISO CD size in MB" )

    (opt,args) = oparser.parse_args(argv)

    if len(args) != 1:
        print("wrong number of arguments", file=sys.stderr)
        oparser.print_help()
        sys.exit(20)

    if not opt.rfs_only:
        try:
            project = ElbeProject( args[0], logpath=opt.log,
                    override_buildtype=opt.buildtype,
                    skip_validate=opt.skip_validation )
        except ValidationError as e:
            print(str (e), file=sys.stderr)
            print("xml validation failed. Bailing out", file=sys.stderr)
            sys.exit(20)

        builddir = project.builddir
        rfs = project.buildenv.rfs
        xml = project.xml
        arch = xml.text("project/arch", key="arch" )
        codename = xml.text("project/suite" )
        log = project.log
        init_codename = xml.get_initvm_codename ()
    else:
        builddir = os.path.abspath( os.path.curdir )
        rfs = ChRootFilesystem( args[0] )
        arch = opt.arch
        codename = opt.codename
        init_codename = opt.init_codename
        xml = None
        if opt.log:
            log = ASCIIDocLog( opt.log )
        else:
            log = StdoutLog()

    generated_files = []
    if opt.source:
        with rfs:
            generated_files += mk_source_cdrom( rfs, arch, codename,
                                                init_codename, builddir, log,
                                                opt.cdrom_size )

    if opt.binary:
        with rfs:
            generated_files += mk_binary_cdrom( rfs, arch, codename,
                                                init_codename, xml, builddir, log,
                    opt.cdrom_size )

    print("")
    print("Image Build finished !")
    print("")
    print("Files generated:")
    for f in generated_files:
        print(" %s"%f)

