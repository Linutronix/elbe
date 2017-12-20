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

import sys

from optparse import OptionParser

from elbepack.elbeproject import ElbeProject
from elbepack.elbexml import ValidationError


def run_command(argv):

    oparser = OptionParser(
        usage="usage: %prog hdimg --target <dir> --output <out> <xmlfile>")
    oparser.add_option("--target", dest="target",
                       help="target directory",
                       metavar="FILE")
    oparser.add_option("-o", "--output", dest="output",
                       help="name of logfile")
    oparser.add_option("--buildtype", dest="buildtype",
                       help="Override the buildtype")
    oparser.add_option("--skip-validation", action="store_true",
                       dest="skip_validation", default=False,
                       help="Skip xml schema validation")
    oparser.add_option("--skip-grub", action="store_true",
                       dest="skip_grub", default=False,
                       help="Skip grub install")
    oparser.add_option(
        "--grub-version",
        type="int",
        dest="grub_version",
        default=202,
        help="use specific grub version (possible values are 0, 199 and 202)")

    (opt, args) = oparser.parse_args(argv)

    if len(args) != 1:
        print("Wrong number of arguments")
        oparser.print_help()
        sys.exit(20)

    if not opt.target:
        print("No directory specified!")
        oparser.print_help()
        sys.exit(20)

    if not opt.output:
        print("No Log output")
        oparser.print_help()
        sys.exit(20)

    if opt.skip_grub:
        opt.grub_version = 0

    if opt.grub_version not in [0, 199, 202]:
        print("invalid grub version")
        oparser.print_help()
        sys.exit(20)

    try:
        project = ElbeProject(opt.target, override_buildtype=opt.buildtype,
                              xmlpath=args[0], logpath=opt.output,
                              skip_validate=opt.skip_validation)
    except ValidationError as e:
        print(str(e))
        print("xml validation failed. Bailing out")
        sys.exit(20)

    project.targetfs.part_target(opt.target, opt.grub_version)
