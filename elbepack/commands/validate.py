# ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (c) 2013, 2017 Manuel Traut <manut@linutronix.de>
# Copyright (c) 2014-2015 Torben Hohn <torbenh@linutronix.de>
#
# SPDX-License-Identifier: GPL-3.0-or-later

import sys
import os
from optparse import OptionParser
from elbepack.validate import validate_xml
from elbepack.elbexml import ElbeXML, ValidationMode, ValidationError


def run_command(argv):
    oparser = OptionParser(usage="usage: %prog validate <xmlfile>")
    oparser.add_option("--validate-urls", dest="validate_urls",
                       help="try to access specified repositories",
                       default=False, action="store_true")

    (opt, args) = oparser.parse_args(argv)

    if not args:
        oparser.print_help()
        sys.exit(20)

    if not os.path.exists(args[0]):
        print(f"{args[0]} - file not found")
        oparser.print_help()
        sys.exit(20)

    validation = validate_xml(args[0])
    if validation:
        print("validation failed")
        for i in validation:
            print(i)
        sys.exit(20)

    if opt.validate_urls:
        try:
            ElbeXML(args[0], url_validation=ValidationMode.CHECK_ALL)
        except ValidationError as e:
            print(e)
            sys.exit(20)

    sys.exit(0)
