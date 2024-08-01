# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2013-2018 Linutronix GmbH

import argparse
import subprocess
import sys

from elbepack import virtapt
from elbepack.aptpkgutils import XMLPackage
from elbepack.changelogxml import changelogs_xml
from elbepack.elbexml import ElbeXML
from elbepack.pkgutils import ChangelogNeedsDependency, extract_pkg_changelog
from elbepack.validate import validate_xml


def build_changelog_xml(v, changelogs, update_packages):
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

    clx.write(changelogs)


def run_command(argv):

    aparser = argparse.ArgumentParser(prog='elbe check_updates')
    aparser.add_argument(
        '-s',
        '--script',
        dest='script',
        help='filename of script to run when an update is required')
    aparser.add_argument('--skip-validation', action='store_true',
                         dest='skip_validation', default=False,
                         help='Skip xml schema validation')
    aparser.add_argument(
        '-c',
        '--changelogs',
        dest='changelogs',
        help='filename of changelog xml file')
    aparser.add_argument('source_xmlfile')
    args = aparser.parse_args(argv)

    if not args.skip_validation:
        validation = validate_xml(args.source_xmlfile)
        if validation:
            print('xml validation failed. Bailing out')
            for i in validation:
                print(i)
            sys.exit(52)

    print(f'checking {args.source_xmlfile}')

    xml = ElbeXML(args.source_xmlfile)

    fullp = xml.node('fullpkgs')

    v = virtapt.VirtApt(xml)

    for p in fullp:
        pname = p.et.text

        if p.bool_attr('auto'):
            v.mark_install(pname)

    errors = 0
    required_updates = 0

    update_packages = []

    for p in fullp:
        xp = XMLPackage(p)
        pname = p.et.text

        if not v.has_pkg(xp.name):
            if not xp.is_auto_installed:
                print(
                    f'{xp.name} does not exist in cache but is specified in '
                    'pkg-list')
                errors += 1
            else:
                print(f'{xp.name} is no more required')
                required_updates += 1

            continue

        if v.marked_install(xp.name):
            cver = v.get_candidate_ver(xp.name)
            if xp.installed_version != cver:
                print(f'{xp.name}: {xp.installed_version} != {cver}')
                required_updates += 1

                if args.changelogs:
                    v.mark_pkg_download(xp.name)
                    xp.candidate_version = cver
                    update_packages.append(xp)

    sys.stdout.flush()
    sys.stderr.flush()
    if errors > 0:
        print(f'{errors} Errors occured, xml files needs fixing')
        if args.script:
            subprocess.run([args.script, 'ERRORS', args.source_xmlfile])
    elif required_updates > 0:
        print(f'{required_updates} updates required')

        if args.changelogs:
            build_changelog_xml(v, args.changelogs, update_packages)

        if args.script:
            subprocess.run([args.script, 'UPDATE', args.source_xmlfile])
    else:
        print('No Updates available')

    v.delete()
