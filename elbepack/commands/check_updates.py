# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2013-2018 Linutronix GmbH

import sys

from optparse import OptionParser

from elbepack import virtapt
from elbepack.validate import validate_xml
from elbepack.shellhelper import system
from elbepack.elbexml import ElbeXML
from elbepack.pkgutils import extract_pkg_changelog, ChangelogNeedsDependency
from elbepack.aptpkgutils import XMLPackage
from elbepack.changelogxml import changelogs_xml


def build_changelog_xml(v, opt, update_packages):
    v.do_downloads()

    clx = changelogs_xml()

    for xp in update_packages:
        try:
            f = v.get_downloaded_pkg(xp.name)
            log = extract_pkg_changelog(f)
        except ChangelogNeedsDependency as e:
            v.mark_pkg_download(e.pkgname)
            v.do_downloads()
            extra = v.get_downloaded_pkg(e.pkgname)
            log = extract_pkg_changelog(f, extra)

        clx.add_pkg_changelog(xp, log)

    clx.write(opt.changelogs)


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
    oparser.add_option(
        "-c",
        "--changelogs",
        dest="changelogs",
        help="filename of changelog xml file")
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

    print(f"checking {args[0]}")

    xml = ElbeXML(args[0])

    fullp = xml.node("fullpkgs")

    arch = xml.text("project/buildimage/arch", key="arch")

    v = virtapt.VirtApt(xml)

    for p in fullp:
        pname = p.et.text
        pauto = p.et.get('auto')

        if pauto != "true":
            v.mark_install(pname)

    errors = 0
    required_updates = 0

    update_packages = []

    for p in fullp:
        xp = XMLPackage(p, arch)
        pname = p.et.text
        pauto = p.et.get('auto')

        if not v.has_pkg(xp.name):
            if not xp.is_auto_installed:
                print(
                    f"{xp.name} does not exist in cache but is specified in "
                    "pkg-list")
                errors += 1
            else:
                print(f"{xp.name} is no more required")
                required_updates += 1

            continue

        if v.marked_install(xp.name):
            cver = v.get_candidate_ver(xp.name)
            if xp.installed_version != cver:
                print(f"{xp.name}: {xp.installed_version} != {cver}")
                required_updates += 1

                if opt.changelogs:
                    v.mark_pkg_download(xp.name)
                    xp.candidate_version = cver
                    update_packages.append(xp)

    sys.stdout.flush()
    sys.stderr.flush()
    if errors > 0:
        print(f"{errors} Errors occured, xml files needs fixing")
        if opt.script:
            system(f"{opt.script} ERRORS {args[0]}", allow_fail=True)
    elif required_updates > 0:
        print(f"{required_updates} updates required")

        if opt.changelogs:
            build_changelog_xml(v, opt, update_packages)

        if opt.script:
            system(f"{opt.script} UPDATE {args[0]}", allow_fail=True)
    else:
        print("No Updates available")
