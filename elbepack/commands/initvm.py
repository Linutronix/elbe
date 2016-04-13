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
                        help="directory, where the initvm resides, default is ./initvm")

    oparser.add_option ("--cdrom", dest="cdrom", default=None,
                        help="iso image of Binary cdrom")

    oparser.add_option( "--devel", action="store_true",
                        dest="devel", default=False,
                        help="Install elbe Version from the current working into initvm" )

    oparser.add_option( "--skip-download", action="store_true",
                        dest="skip_download", default=False,
                        help="Skip downloading generated Files" )

    oparser.add_option ("--output", dest="outdir", default=None,
                        help="directory where to save downloaded Files")

    oparser.add_option( "--skip-build-bin", action="store_false",
                        dest="build_bin", default=True,
                        help="Build Binary Repository CDROM, for exact Reproduction" )

    oparser.add_option( "--skip-build-sources", action="store_false",
                        dest="build_sources", default=True,
                        help="Build Source CD" )

    oparser.add_option( "--keep-files", action="store_true",
                        dest="keep_files", default=False,
                        help="don't delete elbe project files in initvm" )

    (opt,args) = oparser.parse_args (sys.argv)
    args = args[2:]

    if len(args) < 1:
        print ('elbe initvm - no subcommand given', file=sys.stderr)
        InitVMAction.print_actions ()
        sys.exit(20)

    directory = opt.directory or os.getcwd() + '/initvm'

    # Use absolute Path
    directory = os.path.abspath (directory)

    try:
        action = InitVMAction (args[0])
    except KeyError:
        print ('elbe initvm - unknown subcommand', file=sys.stderr)
        InitVMAction.print_actions ()
        sys.exit(20)

    try:
        action.execute (directory, opt, args[1:])
    except InitVMError as e:
        print ('InitVM Exception', file=sys.stderr)
        print (e, file=sys.stderr)
        sys.exit(5)
