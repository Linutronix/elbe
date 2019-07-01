# ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (c) 2013, 2015 Torben Hohn <torbenh@linutronix.de>
# Copyright (c) 2013-2014, 2017-2018 Manuel Traut <manut@linutronix.de>
# Copyright (c) 2017 Holger Dengler <dengler@linutronix.de>
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import print_function

import sys

from optparse import OptionParser

from elbepack.treeutils import etree
from elbepack import virtapt
from elbepack.validate import validate_xml
from elbepack.xmldefaults import ElbeDefaults
from elbepack.shellhelper import system
from elbepack.elbexml import ElbeXML


def run_command(argv):

    # pylint: disable=too-many-locals
    # pylint: disable=too-many-statements
    # pylint: disable=too-many-branches

    oparser = OptionParser(
        usage="usage: %prog check_updates [options] <source-xmlfile>")
    oparser.add_option(
        "-s",
        "--script",
        dest="script",
        help="filename of script to run when an update is required")
    oparser.add_option("--skip-validation", action="store_true",
                       dest="skip_validation", default=False,
                       help="Skip xml schema validation")
    (opt, args) = oparser.parse_args(argv)

    if len(args) != 1:
        print("Wrong number of arguments")
        oparser.print_help()
        sys.exit(20)

    if not opt.skip_validation:
        validation = validate_xml(args[0])
        if validation:
            print("xml validation failed. Bailing out")
            for i in validation:
                print(i)
            sys.exit(20)

    print("checking %s" % args[0])

    xml = ElbeXML(args[0])


    apt_sources = xml.text("sources_list").replace("10.0.2.2", "localhost")
    apt_prefs = xml.text("apt_prefs")

    fullp = xml.node("fullpkgs")

    v = virtapt.VirtApt(xml)

    for p in fullp:
        pname = p.et.text
        pver = p.et.get('version')
        pauto = p.et.get('auto')

        if pauto != "true":
            v.mark_install(pname)

    errors = 0
    required_updates = 0

    for p in fullp:
        pname = p.et.text
        pver = p.et.get('version')
        pauto = p.et.get('auto')

        if not v.has_pkg(pname):
            if pauto == 'false':
                print(
                    "%s does not exist in cache but is specified in pkg-list" %
                    pname)
                errors += 1
            else:
                print("%s is no more required" % pname)
                required_updates += 1

            continue

        if v.marked_install(pname):
            cver = v.get_candidate_ver(pname)
            if pver != cver:
                print("%s: %s != %s" % (pname, pver, cver))
                required_updates += 1

    sys.stdout.flush()
    sys.stderr.flush()
    if errors > 0:
        print("%d Errors occured, xml files needs fixing" % errors)
        if opt.script:
            system("%s ERRORS %s" % (opt.script, args[0]), allow_fail=True)
    elif required_updates > 0:
        print("%d updates required" % required_updates)
        if opt.script:
            system("%s UPDATE %s" % (opt.script, args[0]), allow_fail=True)
    else:
        print("No Updates available")
