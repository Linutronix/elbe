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
import io

from elbepack.asciidoclog import StdoutLog
from elbepack.filesystem import Filesystem

def run_command( argv ):
    oparser = OptionParser(usage="usage: %prog genlicence [options] <rfs>")
    oparser.add_option( "--output", dest="output",
                        help="outputfilename" )
    oparser.add_option( "--xml", dest="xml", default=None,
                        help="xml outputfilename" )

    (opt,args) = oparser.parse_args(argv)

    if len(args) != 1:
        print("wrong number of arguments")
        oparser.print_help()
        sys.exit(20)

    chroot = os.path.abspath(args[0])

    rfs = Filesystem( chroot )
    log = StdoutLog()

    if opt.output:
        f = io.open( opt.output, "w+", encoding='utf-8' )
    else:
        f = io.open( 'licence.txt', "w+", encoding='utf-8' )

    rfs.write_licenses(f, log, opt.xml)
    f.close()

