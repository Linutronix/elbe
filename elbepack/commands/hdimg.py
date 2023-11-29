# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2012-2017 Linutronix GmbH

import sys
import logging

from optparse import OptionParser

from elbepack.elbeproject import ElbeProject
from elbepack.elbexml import ValidationError
from elbepack.log import elbe_logging


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
        help="use specific grub version (possible values are 0, 97, and 202)")

    (opt, args) = oparser.parse_args(argv)

    if len(args) != 1:
        print("Wrong number of arguments")
        oparser.print_help()
        sys.exit(65)

    if not opt.target:
        print("No directory specified!")
        oparser.print_help()
        sys.exit(66)

    if not opt.output:
        print("No Log output")
        oparser.print_help()
        sys.exit(67)

    if opt.skip_grub:
        opt.grub_version = 0

    if opt.grub_version not in [0, 97, 202]:
        print("invalid grub version")
        oparser.print_help()
        sys.exit(68)

    with elbe_logging({"files":opt.output}):
        try:
            project = ElbeProject(opt.target,
                                  override_buildtype=opt.buildtype,
                                  xmlpath=args[0],
                                  skip_validate=opt.skip_validation)
        except ValidationError:
            logging.exception("XML validation failed.  Bailing out")
            sys.exit(69)

        project.targetfs.part_target(opt.target, opt.grub_version)
