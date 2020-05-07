# ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (c) 2015-2016 Torben Hohn <torben.hohn@linutronix.de>
# Copyright (c) 2017 Manuel Traut <manut@linutronix.de>
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import print_function

import sys

from optparse import OptionParser
from elbepack.pbuilderaction import PBuilderAction, PBuilderError
from elbepack.xmlpreprocess import PreprocessWrapper


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

    oparser.add_option("--cpuset", default=-1, type="int",
                       help="Limit cpuset of pbuilder commands (bitmask) "
                            "(defaults to -1 for all CPUs)")

    oparser.add_option("--profile", dest="profile", default="",
                       help="profile that shall be built")

    oparser.add_option("--cross", dest="cross", default=False,
                       action="store_true",
                       help="Creates an environment for crossbuilding if "
                            "combined with create. Combined with build it"
                            " will use this environment.")

    PreprocessWrapper.add_options(oparser)

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
