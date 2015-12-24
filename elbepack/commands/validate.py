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
from optparse import OptionParser
from elbepack.validate import validate_xml


def run_command( argv ):
    oparser = OptionParser( usage="usage: %prog validate <xmlfile>")
    (opt,args) = oparser.parse_args(argv)

    if len(args) != 1:
        print "Wrong number of arguments"
        oparser.print_help()
        sys.exit(20)

    validation = validate_xml (args[0])
    if len (validation) == 0:
        sys.exit (0)
    else:
        print "validation failed"
        for i in validation:
            print i
        sys.exit(20)

