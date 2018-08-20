# ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (c) 2013, 2015 Torben Hohn <torbenh@linutronix.de>
# Copyright (c) 2013-2014, 2017-2018 Manuel Traut <manut@linutronix.de>
# Copyright (c) 2017 Holger Dengler <dengler@linutronix.de>
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import print_function

import os
import sys

from optparse import OptionParser

from elbepack.treeutils import etree
from elbepack import virtapt
from elbepack.validate import validate_xml
from elbepack.xmldefaults import ElbeDefaults


def run_command(argv):

    # pylint: disable=too-many-locals
    # pylint: disable=too-many-statements

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
        if len(validation) != 0:
            print("xml validation failed. Bailing out")
            for i in validation:
                print(i)
            sys.exit(20)

    print("checking %s" % args[0])

    xml = etree(args[0])

    if xml.has("project/buildtype"):
        buildtype = xml.text("/project/buildtype")
    else:
        buildtype = "nodefaults"

    defs = ElbeDefaults(buildtype)

    arch = xml.text("project/buildimage/arch", default=defs, key="arch")
    suite = xml.text("project/suite")

    apt_sources = xml.text("sources_list").replace("10.0.2.2", "localhost")
    apt_prefs = xml.text("apt_prefs")

    fullp = xml.node("fullpkgs")

    v = virtapt.VirtApt(arch, suite, apt_sources, apt_prefs)

    d = virtapt.apt_pkg.DepCache(v.cache)
    d.read_pinfile(v.projectpath + "/etc/apt/preferences")

    for p in fullp:
        pname = p.et.text
        pver = p.et.get('version')
        pauto = p.et.get('auto')

        if pauto != "true":
            d.mark_install(v.cache[pname])

    errors = 0
    required_updates = 0

    for p in fullp:
        pname = p.et.text
        pver = p.et.get('version')
        pauto = p.et.get('auto')

        if pname not in v.cache:
            if pauto == 'false':
                print(
                    "%s does not exist in cache but is specified in pkg-list" %
                    pname)
                errors += 1
            else:
                print("%s is no more required" % pname)
                required_updates += 1

            continue

        centry = v.cache[pname]

        if d.marked_install(centry):
            cver = d.get_candidate_ver(v.cache[pname]).ver_str
            if pver != cver:
                print("%s: %s != %s" % (pname, pver, cver))
                required_updates += 1

    sys.stdout.flush()
    sys.stderr.flush()
    if errors > 0:
        print("%d Errors occured, xml files needs fixing" % errors)
        if opt.script:
            os.system("%s ERRORS %s" % (opt.script, args[0]))
    elif required_updates > 0:
        print("%d updates required" % required_updates)
        if opt.script:
            os.system("%s UPDATE %s" % (opt.script, args[0]))
    else:
        print("No Updates available")
