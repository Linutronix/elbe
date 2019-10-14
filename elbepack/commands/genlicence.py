# ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (c) 2014, 2016 Torben Hohn <torben.hohn@linutronix.de>
# Copyright (c) 2015, 2017 Manuel Traut <manut@linutronix.de>
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import print_function

from optparse import OptionParser
import sys
import io
import logging

from elbepack.elbexml import ValidationError, ValidationMode
from elbepack.elbeproject import ElbeProject
from elbepack.log import elbe_logging


def run_command(argv):
    oparser = OptionParser(usage="usage: %prog genlicence [options] <project>")
    oparser.add_option("--output", dest="output",
                       help="outputfilename")
    oparser.add_option("--xml", dest="xml", default=None,
                       help="xml outputfilename")
    oparser.add_option("--buildtype", dest="buildtype",
                       help="Override the buildtype")
    oparser.add_option("--skip-validation", action="store_true",
                       dest="skip_validation", default=False,
                       help="Skip xml schema validation")

    (opt, args) = oparser.parse_args(argv)

    if len(args) != 1:
        print("wrong number of arguments")
        oparser.print_help()
        sys.exit(20)

    with elbe_logging({"streams": sys.stdout}):
        try:
            project = ElbeProject(args[0],
                                  override_buildtype=opt.buildtype,
                                  skip_validate=opt.skip_validation,
                                  url_validation=ValidationMode.NO_CHECK)
        except ValidationError:
            logging.exception("XML validation failed.  Bailing out")
            sys.exit(20)

        if opt.output:
            f = io.open(opt.output, "w+", encoding='utf-8')
        else:
            f = io.open('licence.txt', "w+", encoding='utf-8')

        pkglist = project.get_rpcaptcache().get_installed_pkgs()
        pkgnames = [p.name for p in pkglist]

        project.buildenv.rfs.write_licenses(f, pkgnames, opt.xml)
        f.close()
