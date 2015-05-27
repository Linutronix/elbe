# ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (C) 2014  Linutronix GmbH
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

import sys
import os

from optparse import OptionParser
from elbepack.initvmaction import InitVMAction, InitVMError

def run_command (argv):
    oparser = OptionParser (usage="usage: elbe initvm [options] <command>")

    oparser.add_option ("--directory", dest="directory", default=None,
                        help="directory, where the initvm resides")

    (opt,args) = oparser.parse_args (sys.argv)
    args = args[2:]

    if len(args) < 1:
        print ('elbe initvm - no subcommand given', file=sys.stderr)
        InitVMAction.print_actions ()
        return

    directory = opt.directory or os.getcwd()

    try:
        action = InitVMAction (args[0])
    except KeyError:
        print ('elbe initvm - unknown subcommand', file=sys.stderr)
        InitVMAction.print_actions ()
        sys.exit(20)

    try:
        action.execute (directory, args[1:])
    except InitVMError as e:
        print ('InitVM Exception', file=sys.stderr)
        print (e, file=sys.stderr)
        sys.exit(5)
