# ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (c) 2014-2015 Torben Hohn <torbenh@linutronix.de>
# Copyright (c) 2014 Stefan Gast <stefan.gast@linutronix.de>
# Copyright (c) 2014-2015, 2017 Manuel Traut <manut@linutronix.de>
# Copyright (c) 2017 Philipp Arras <philipp.arras@linutronix.de>
#
# SPDX-License-Identifier: GPL-3.0-or-later

from optparse import OptionParser
import sys
import os
import logging

from elbepack.elbeproject import ElbeProject
from elbepack.elbexml import ValidationError, ValidationMode
from elbepack.shellhelper import system, CommandError
from elbepack.log import elbe_logging


def run_command(argv):
    oparser = OptionParser(
        usage="usage: %prog chroot [options] <builddir> [cmd]")
    oparser.add_option("--skip-validation", action="store_true",
                       dest="skip_validation", default=False,
                       help="Skip xml schema validation")
    oparser.add_option("--target", action="store_true", dest="target",
                       help="chroot into target instead of buildenv",
                       default=False)
    oparser.add_option("--buildtype", dest="buildtype",
                       help="Override the buildtype")

    (opt, args) = oparser.parse_args(argv)

    if len(args) < 1:
        print("wrong number of arguments")
        oparser.print_help()
        sys.exit(20)

    with elbe_logging({"streams":sys.stdout}):
        try:
            project = ElbeProject(args[0],
                                  override_buildtype=opt.buildtype,
                                  skip_validate=opt.skip_validation,
                                  url_validation=ValidationMode.NO_CHECK)
        except ValidationError:
            logging.exception("XML validation failed.  Bailing out")
            sys.exit(20)

        os.environ["LANG"] = "C"
        os.environ["LANGUAGE"] = "C"
        os.environ["LC_ALL"] = "C"
        # TODO: howto set env in chroot?
        os.environ["PS1"] = project.xml.text('project/name') + r': \w\$'

        cmd = "/bin/bash"

        if len(args) > 1:
            cmd = ""
            cmd2 = args[1:]
            for c in cmd2:
                cmd += (c + " ")

        if opt.target:
            try:
                with project.targetfs:
                    system("/usr/sbin/chroot %s %s" %
                           (project.targetpath, cmd))
            except CommandError as e:
                print(repr(e))
        else:
            try:
                with project.buildenv:
                    system("/usr/sbin/chroot %s %s" %
                           (project.chrootpath, cmd))
            except CommandError as e:
                print(repr(e))
