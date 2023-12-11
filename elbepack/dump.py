# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2014-2017 Linutronix GmbH

import logging

from fnmatch import fnmatchcase
from datetime import datetime

from apt import Cache

from elbepack.archivedir import archive_tmpfile
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

    validation.info("ELBE Package validation")
    validation.info("=======================")
    validation.info("")
    validation.info("Package List validation")
    validation.info("-----------------------")
    validation.info("")

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
            if ver and not fnmatchcase(pkg.installed_version, ver):
                validation.error("Package '%s' version '%s' does not match installed version %s",
                                 name, ver, pkg.installed_version)
                errors += 1
                continue

    if errors == 0:
        validation.info("No Errors found")

    if not fullpkgs:
        return

    validation.info("Full Packagelist validation")
    validation.info("---------------------------")
    validation.info("")
    errors = 0

    pindex = {}
    for p in fullpkgs:
        name = p.et.text
        ver = p.et.get('version')
        md5 = p.et.get('md5')
        sha256 = p.et.get('sha256')

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

        if not fnmatchcase(pkg.installed_version, ver):
            validation.error("Package '%s' version %s does not match installed version %s",
                             name, ver, pkg.installed_version)
            errors += 1
            continue

        if md5:
            if pkg.installed_md5 != md5:
                validation.error("Package '%s' md5 %s does not match installed md5 %s",
                                 name, md5, pkg.installed_md5)
                errors += 1

        if sha256:
            if pkg.installed_sha256 != sha256:
                validation.error("Package '%s' sha256 %s does not match installed sha256 %s",
                                 name, sha256, pkg.installed_sha256)
                errors += 1

        if not md5 and not sha256:
            validation.error("Package '%s' has no hash setup in package list.",
                             name)
            errors += 1

    for cp in cache.get_installed_pkgs():
        if cp.name not in pindex:
            validation.error("Additional package %s installed, that was not requested",
                             cp.name)
            errors += 1

    if errors == 0:
        validation.info("No Errors found")


def elbe_report(xml, buildenv, cache, targetfs):

    rfs = buildenv.rfs

    report.info("ELBE Report for Project %s\n\n"
                "Report timestamp: %s\n"
                "elbe: %s",
                xml.text("project/name"),
                datetime.now().strftime("%Y%m%d-%H%M%S"),
                str(elbe_version))

    slist = rfs.read_file('etc/apt/sources.list')
    report.info("")
    report.info("Apt Sources dump")
    report.info("----------------")
    report.info("")
    report.info("%s", slist)
    report.info("")

    try:
        prefs = rfs.read_file("etc/apt/preferences")
    except IOError:
        prefs = ""

    report.info("")
    report.info("Apt Preferences dump")
    report.info("--------------------")
    report.info("")
    report.info("%s", prefs)
    report.info("")
    report.info("Installed Packages List")
    report.info("-----------------------")
    report.info("")

    instpkgs = cache.get_installed_pkgs()
    for p in instpkgs:
        report.info("|%s|%s|%s", p.name, p.installed_version, p.origin)

    index = cache.get_fileindex(removeprefix='/usr')
    mt_index = targetfs.mtime_snap()

    if xml.has("archive") and not xml.text("archive") is None:
        with archive_tmpfile(xml.text("archive")) as fp:
            do(f'tar xvfj "{fp.name}" -h -C "{targetfs.path}"')
        mt_index_postarch = targetfs.mtime_snap()
    else:
        mt_index_postarch = mt_index

    if xml.has("target/finetuning"):
        do_finetuning(xml, buildenv, targetfs)
        mt_index_post_fine = targetfs.mtime_snap()
    else:
        mt_index_post_fine = mt_index_postarch

    report.info("")
    report.info("File List")
    report.info("---------")
    report.info("")

    tgt_pkg_list = set()

    for fpath, _ in targetfs.walk_files():
        unprefixed = fpath[len('/usr'):] if fpath.startswith('/usr') else fpath
        if unprefixed in index:
            pkg = index[unprefixed]
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

    report.info("")
    report.info("Deleted Files")
    report.info("-------------")
    report.info("")

    for fpath in list(mt_index.keys()):
        if fpath not in mt_index_post_fine:
            unprefixed = fpath[len('/usr'):] if fpath.startswith('/usr') else fpath
            if unprefixed in index:
                pkg = index[unprefixed]
            else:
                pkg = "postinst generated"
            report.info("|+%s+|%s", fpath, pkg)

    report.info("")
    report.info("Target Package List")
    report.info("-------------------")
    report.info("")

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
            f.write(f"{p.name} {p.installed_version} {p.installed_md5}\n")

    if xml.has("target/pkgversionlist"):
        f.close()

    if not xml.has("archive") or xml.text("archive") is None:
        return list(tgt_pkg_list)

    validation.info("")
    validation.info("Archive validation")
    validation.info("------------------")
    validation.info("")

    for fpath in list(mt_index_postarch.keys()):
        if (fpath not in mt_index or
           mt_index_postarch[fpath] != mt_index[fpath]):
            if fpath not in mt_index_post_fine:
                validation.warning("Archive file %s deleted in finetuning",
                                   fpath)
            elif mt_index_post_fine[fpath] != mt_index_postarch[fpath]:
                validation.warning("Archive file %s modified in finetuning",
                                   fpath)
    return list(tgt_pkg_list)
