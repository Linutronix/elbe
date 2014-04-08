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

from elbepack.asciidoclog import StdoutLog
from elbepack.rfs import BuildEnv
from elbepack.elbexml import ElbeXML, ValidationError

from elbepack.filesystem import BuildImgFs

def run_command( argv ):
    oparser = OptionParser(usage="usage: %prog genlicence [options] <rfs>")
    oparser.add_option( "--output", dest="output",
                        help="outputfilename" )

    (opt,args) = oparser.parse_args(argv)

    if len(args) != 1:
        print "wrong number of arguments"
        oparser.print_help()
        sys.exit(20)

    chroot = os.path.abspath(args[0])

    rfs = BuildImgFs( chroot, None )
    log = StdoutLog()

    if opt.output:
        f = open( opt.output, "w+" )
    else:
        f = open( 'licence.txt', "w+" )

    rfs.write_licenses(f, log)
    f.close()

