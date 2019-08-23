# ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (c) 2012-2015 Torben Hohn <torbenh@linutronix.de>
# Copyright (c) 2013, 2017 Manuel Traut <manut@linutronix.de>
# Copyright (c) 2014 Stefan Gast <stefan.gast@linutronix.de>
#
# SPDX-License-Identifier: GPL-3.0-or-later

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
        help="use specific grub version (possible values are 0 and 202)")

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

    if opt.grub_version not in [0, 202]:
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
