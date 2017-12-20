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

from optparse import OptionParser
from elbepack.pbuilderaction import PBuilderAction, PBuilderError


def run_command(argv):
    oparser = OptionParser(usage="usage: elbe pbuilder [options] <command>")

    oparser.add_option("--project", dest="project", default=None,
                       help="project directory on the initvm")

    oparser.add_option("--xmlfile", dest="xmlfile", default=None,
                       help="xmlfile to use")

    oparser.add_option("--writeproject", dest="writeproject", default=None,
                       help="write project name to file")

    oparser.add_option("--skip-download", action="store_true",
                       dest="skip_download", default=False,
                       help="Skip downloading generated Files")

    oparser.add_option(
        "--origfile",
        dest="origfile",
        default=[],
        action="append",
        help="upload orig file")

    oparser.add_option("--output", dest="outdir", default=None,
                       help="directory where to save downloaded Files")

    (opt, args) = oparser.parse_args(argv)

    if len(args) < 1:
        print("elbe pbuilder - no subcommand given", file=sys.stderr)
        PBuilderAction.print_actions()
        return

    try:
        action = PBuilderAction(args[0])
    except KeyError:
        print("elbe pbuilder - unknown subcommand", file=sys.stderr)
        PBuilderAction.print_actions()
        sys.exit(20)

    try:
        action.execute(opt, args[1:])
    except PBuilderError as e:
        print("PBuilder Exception", file=sys.stderr)
        print(e, file=sys.stderr)
        sys.exit(5)
