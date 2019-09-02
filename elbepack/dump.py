# ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (c) 2014-2015 Torben Hohn <torbenh@linutronix.de>
# Copyright (c) 2015-2017 Manuel Traut <manut@linutronix.de>
# Copyright (c) 2017 John Ogness <john.ogness@linutronix.de>
#
# SPDX-License-Identifier: GPL-3.0-or-later

import logging

from datetime import datetime

from apt import Cache

from elbepack.finetuning import do_finetuning
from elbepack.filesystem import hostfs
from elbepack.version import elbe_version
from elbepack.aptpkgutils import APTPackage
from elbepack.shellhelper import do

report = logging.getLogger("report")
validation = logging.getLogger("validation")

def get_initvm_pkglist():
    cache = Cache()
    cache.open()
    pkglist = [APTPackage(p) for p in cache if p.is_installed]

    return pkglist


def dump_fullpkgs(xml, rfs, cache):
    xml.clear_full_pkglist()

    instpkgs = cache.get_installed_pkgs()
    for p in instpkgs:
        xml.append_full_pkg(p)

    sources_list = xml.xml.ensure_child('sources_list')
    slist = rfs.read_file("etc/apt/sources.list")
    sources_list.set_text(slist)

    try:
        preferences = xml.xml.ensure_child('apt_prefs')
        prefs = rfs.read_file("etc/apt/preferences")
        preferences.set_text(prefs)
    except IOError:
        pass


def dump_debootstrappkgs(xml, cache):
    xml.clear_debootstrap_pkglist()

    instpkgs = cache.get_installed_pkgs()
    for p in instpkgs:
        xml.append_debootstrap_pkg(p)


def dump_initvmpkgs(xml):
    xml.clear_initvm_pkglist()

    instpkgs = get_initvm_pkglist()
    for p in instpkgs:
        xml.append_initvm_pkg(p)

    sources_list = xml.xml.ensure_child('initvm_sources_list')
    slist = hostfs.read_file("etc/apt/sources.list")
    sources_list.set_text(slist)

    try:
        preferences = xml.xml.ensure_child('initvm_apt_prefs')
        prefs = hostfs.read_file("etc/apt/preferences")
        preferences.set_text(prefs)
    except IOError:
        pass


def check_full_pkgs(pkgs, fullpkgs, cache):

    # pylint: disable=too-many-statements
    # pylint: disable=too-many-branches


    validation.info("ELBE Package validation")
    validation.info("Package List validation")

    errors = 0

    if pkgs:
        for p in pkgs:
            name = p.et.text
            nomulti_name = name.split(":")[0]
            if not cache.has_pkg(nomulti_name):
                validation.error("Package '%s' does not exist", nomulti_name)
                errors += 1
                continue

            if not cache.is_installed(nomulti_name):
                validation.error("Package '%s' is not installed", nomulti_name)
                errors += 1
                continue

            ver = p.et.get('version')
            pkg = cache.get_pkg(nomulti_name)
            if ver and (pkg.installed_version != ver):
                validation.error("Package '%s' version '%s' does not match installed version %s",
                                 name, ver, pkg.installed_version)
                errors += 1
                continue

    if errors == 0:
        validation.info("No Errors found")

    if not fullpkgs:
        return

    validation.info("Full Packagelist validation")
    errors = 0

    pindex = {}
    for p in fullpkgs:
        name = p.et.text
        ver = p.et.get('version')
        md5 = p.et.get('md5')

        pindex[name] = p

        if not cache.has_pkg(name):
            validation.error("Package '%s' does not exist", name)
            errors += 1
            continue

        if not cache.is_installed(name):
            validation.error("Package '%s' is not installed", name)
            errors += 1
            continue

        pkg = cache.get_pkg(name)

        if pkg.installed_version != ver:
            validation.error("Package '%s' version %s does not match installed version %s",
                             name, ver, pkg.installed_version)
            errors += 1
            continue

        if pkg.installed_md5 != md5:
            validation.error("Package '%s' md5 %s does not match installed md5 %s",
                             name, md5, pkg.installed_md5)
            errors += 1

    for cp in cache.get_installed_pkgs():
        if cp.name not in pindex:
            validation.error("Additional package %s installed, that was not requested",
                             cp.name)
            errors += 1

    if errors == 0:
        validation.info("No Errors found")


def elbe_report(xml, buildenv, cache, targetfs):

    # pylint: disable=too-many-arguments
    # pylint: disable=too-many-locals
    # pylint: disable=too-many-statements
    # pylint: disable=too-many-branches

    rfs = buildenv.rfs

    report.info("ELBE Report for Project %s\n"
                "Report timestamp: %s\n"
                "elbe: %s",
                xml.text("project/name"),
                datetime.now().strftime("%Y%m%d-%H%M%S"),
                str(elbe_version))

    slist = rfs.read_file('etc/apt/sources.list')
    report.info("Apt Sources dump\n%s", slist)

    try:
        prefs = rfs.read_file("etc/apt/preferences")
    except IOError:
        prefs = ""

    report.info("Apt Preferences dump\n%s", prefs)

    report.info("Installed Packages List")

    instpkgs = cache.get_installed_pkgs()
    for p in instpkgs:
        report.info("|%s|%s|%s", p.name, p.installed_version, p.origin)

    index = cache.get_fileindex()
    mt_index = targetfs.mtime_snap()

    report.info("Archive extract")

    if xml.has("archive") and not xml.text("archive") is None:
        with xml.archive_tmpfile() as fp:
            do('tar xvfj "%s" -h -C "%s"' % (fp.name, targetfs.path))
        mt_index_postarch = targetfs.mtime_snap()
    else:
        mt_index_postarch = mt_index

    report.info("Finetuning log")

    if xml.has("target/finetuning"):
        do_finetuning(xml, buildenv, targetfs)
        mt_index_post_fine = targetfs.mtime_snap()
    else:
        mt_index_post_fine = mt_index_postarch



    report.info("Fileslist")

    tgt_pkg_list = set()

    for fpath, _ in targetfs.walk_files():
        if fpath in index:
            pkg = index[fpath]
            tgt_pkg_list.add(pkg)
        else:
            pkg = "postinst generated"

        if fpath in mt_index_post_fine:
            if fpath in mt_index_postarch:
                if mt_index_post_fine[fpath] != mt_index_postarch[fpath]:
                    pkg = "modified finetuning"
                elif fpath in mt_index:
                    if mt_index_postarch[fpath] != mt_index[fpath]:
                        pkg = "from archive"
                    # else leave pkg as is
                else:
                    pkg = "added in archive"
            else:
                pkg = "added in finetuning"
        # else leave pkg as is

        report.info("|+%s+|%s", fpath, pkg)


    report.info("Deleted Files")
    for fpath in list(mt_index.keys()):
        if fpath not in mt_index_post_fine:
            if fpath in index:
                pkg = index[fpath]
            else:
                pkg = "postinst generated"
            report.info("|+%s+|%s", fpath, pkg)

    report.info("Target Package List")

    instpkgs = cache.get_installed_pkgs()
    pkgindex = {}
    for p in instpkgs:
        pkgindex[p.name] = p

    if xml.has("target/pkgversionlist"):
        targetfs.remove('etc/elbe_pkglist')
        f = targetfs.open('etc/elbe_pkglist', 'w')
    for pkg in tgt_pkg_list:
        p = pkgindex[pkg]
        report.info("|%s|%s|%s|%s",
                    p.name,
                    p.installed_version,
                    p.is_auto_installed,
                    p.installed_md5)
        if xml.has("target/pkgversionlist"):
            f.write(
                "%s %s %s\n" %
                (p.name,
                 p.installed_version,
                 p.installed_md5))

    if xml.has("target/pkgversionlist"):
        f.close()

    if not xml.has("archive") or xml.text("archive") is None:
        return


    validation.info("Archive validation")

    errors = 0

    for fpath in list(mt_index_postarch.keys()):
        if fpath not in mt_index or \
                mt_index_postarch[fpath] != mt_index[fpath]:
            if fpath not in mt_index_post_fine:
                validation.error("Archive file %s deleted in finetuning",
                                 fpath)
                errors += 1
            elif mt_index_post_fine[fpath] != mt_index_postarch[fpath]:
                validation.error("Archive file %s modified in finetuning",
                                 fpath)
                errors += 1

    if errors == 0:
        validation.info("No Errors found")
