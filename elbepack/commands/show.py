# ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (c) 2013-2015, 2017 Manuel Traut <manut@linutronix.de>
# Copyright (c) 2015 Torben Hohn <torbenh@linutronix.de>
#
# SPDX-License-Identifier: GPL-3.0-or-later

import sys

from optparse import OptionParser

from elbepack.treeutils import etree
from elbepack.validate import validate_xml



def run_command(argv):

    # pylint: disable=too-many-branches

    oparser = OptionParser(usage="usage: %prog show [options] <filename>")

    oparser.add_option("--verbose", action="store_true", dest="verbose",
                       default=False,
                       help="show detailed project informations")

    oparser.add_option("--skip-validation", action="store_true",
                       dest="skip_validation", default=False,
                       help="Skip xml schema validation")

    (opt, args) = oparser.parse_args(argv)

    if not args:
        print("No Filename specified")
        oparser.print_help()
        sys.exit(20)

    if len(args) > 1:
        print("too many filenames specified")
        oparser.print_help()
        sys.exit(20)

    try:
        if not opt.skip_validation:
            validation = validate_xml(args[0])
            if validation:
                print("xml validation failed. Bailing out")
                for i in validation:
                    print(i)
                sys.exit(20)

        xml = etree(args[0])
    except BaseException:
        print("Unable to open xml File. Bailing out")
        sys.exit(20)

    if not xml.has("./project"):
        print("no project description available")
        sys.exit(20)

    print(f"== {args[0]} ==")
    print(f"Debian suite: {xml.text('./project/suite')}")
    for s in xml.text("./project/description").splitlines():
        print(f"{s.strip()}")
    if opt.verbose:
        if xml.has("./target/passwd"):
            print(f"root password: {xml.text('./target/passwd')}")
        print(
            "primary_mirror: "
            f"{xml.text('./project/mirror/primary_proto')}://"
            f"{xml.text('./project/mirror/primary_host')}"
            f"{xml.text('./project/mirror/primary_path')}")
        if xml.has("./project/mirror/url-list"):
            print("additional mirrors:")
            for url in xml.node("./project/mirror/url-list"):
                if url.has("binary"):
                    print(f"    deb {url.text('binary').strip()}")
                if url.has("source"):
                    print(f"    deb-src {url.text('source').strip()}")
        if xml.has("./target/pkg-list"):
            print("packages:")
            for pkg in xml.node("./target/pkg-list"):
                print(f"    {pkg.et.text}")
        print(f"skip package validation: {xml.has('./project/noauth')}")
        print(f"archive embedded?        {xml.has('./archive')}")
