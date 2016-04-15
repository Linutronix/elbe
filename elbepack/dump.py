# ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (C) 2013  Linutronix GmbH
#
# This file is part of ELBE.
#
# ELBE is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# ELBE is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with ELBE.  If not, see <http://www.gnu.org/licenses/>.

from elbepack.asciidoclog import ASCIIDocLog
from datetime import datetime
from elbepack.finetuning import do_finetuning
from elbepack.filesystem import hostfs
from elbepack.version import elbe_version

from elbepack.aptpkgutils import APTPackage
from apt import Cache

import warnings

def get_initvm_pkglist ():
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore",category=DeprecationWarning)
        cache = Cache ()
        cache.open ()
        pkglist = [APTPackage (p) for p in cache if p.is_installed]
        try:
            eb = APTPackage( cache ['elbe-bootstrap'] )
            pkglist.append (eb)
        # elbe bootstrap is not installed on pc running elbe
        except KeyError:
            pass

    return pkglist

def dump_fullpkgs( xml, rfs, cache ):
    xml.clear_full_pkglist()

    instpkgs = cache.get_installed_pkgs()
    for p in instpkgs:
        xml.append_full_pkg( p )

    sources_list = xml.xml.ensure_child( 'sources_list' )
    slist = rfs.read_file("etc/apt/sources.list")
    sources_list.set_text( slist )

    try:
        preferences = xml.xml.ensure_child( 'apt_prefs' )
        prefs = rfs.read_file("etc/apt/preferences")
        preferences.set_text(prefs)
    except IOError:
        pass

def dump_debootstrappkgs( xml, cache ):
    xml.clear_debootstrap_pkglist()

    instpkgs = cache.get_installed_pkgs()
    for p in instpkgs:
        xml.append_debootstrap_pkg( p )

def dump_initvmpkgs (xml):
    xml.clear_initvm_pkglist ()

    instpkgs = get_initvm_pkglist ()
    for p in instpkgs:
        xml.append_initvm_pkg( p )

    sources_list = xml.xml.ensure_child( 'initvm_sources_list' )
    slist = hostfs.read_file("etc/apt/sources.list")
    sources_list.set_text( slist )

    try:
        preferences = xml.xml.ensure_child( 'initvm_apt_prefs' )
        prefs = hostfs.read_file("etc/apt/preferences")
        preferences.set_text(prefs)
    except IOError:
        pass

def check_full_pkgs(pkgs, fullpkgs, errorname, cache):
    elog = ASCIIDocLog(errorname)

    elog.h1("ELBE Package validation")
    elog.h2("Package List validation")

    errors = 0

    for name in [p.et.text for p in pkgs]:

        nomulti_name = name.split(":")[0]
        if not cache.has_pkg(nomulti_name):
            elog.printo( "- package %s does not exist" % nomulti_name )
            errors += 1
            continue

        if not cache.is_installed(nomulti_name):
            elog.printo( "- package %s is not installed" % nomulti_name )
            errors += 1
            continue

    if errors == 0:
        elog.printo( "No Errors found" )

    if not fullpkgs:
        return

    elog.h2("Full Packagelist validation")
    errors = 0

    pindex = {}
    for p in fullpkgs:
        name = p.et.text
        ver  = p.et.get('version')
        md5  = p.et.get('md5')

        pindex[name] = p

        if not cache.has_pkg(name):
            elog.printo( "- package %s does not exist" % name )
            errors += 1
            continue

        if not cache.is_installed(name):
            elog.printo( "- package %s is not installed" % name )
            errors += 1
            continue

        pkg = cache.get_pkg(name)

        if pkg.installed_version != ver:
            elog.printo( "- package %s version %s does not match installed version %s" % (name, ver,  pkg.installed_version) )
            errors += 1
            continue

        if pkg.installed_md5 != md5:
            elog.printo( "- package %s md5 %s does not match installed md5 %s" %
              (name, md5,  pkg.installed_md5) )
            errors += 1

    for cp in cache.get_installed_pkgs():
        if not pindex.has_key(cp.name):
            elog.printo( "additional package %s installed, that was not requested" % cp.name )
            errors += 1

    if errors == 0:
        elog.printo( "No Errors found" )

def elbe_report( xml, buildenv, cache, reportname, targetfs ):
    outf = ASCIIDocLog(reportname)
    rfs = buildenv.rfs

    outf.h1( "ELBE Report for Project " + xml.text("project/name") )

    outf.printo( "report timestamp: "+datetime.now().strftime("%Y%m%d-%H%M%S") )
    outf.printo( "elbe: %s" % str(elbe_version) )

    slist = rfs.read_file('etc/apt/sources.list')
    outf.h2( "Apt Sources dump" )
    outf.verbatim_start()
    outf.print_raw(slist)
    outf.verbatim_end()

    try:
        prefs = rfs.read_file("etc/apt/preferences")
    except IOError:
        prefs = ""

    outf.h2( "Apt Preferences dump" )
    outf.verbatim_start()
    outf.print_raw(prefs)
    outf.verbatim_end()

    outf.h2( "Installed Packages List" )
    outf.table()

    instpkgs = cache.get_installed_pkgs()
    for p in instpkgs:
        outf.printo( "|%s|%s|%s" % (p.name, p.installed_version, p.origin) )
    outf.table()

    # archive extraction is done before and after finetuning the first
    # extraction is needed that the files can be used (copied/moved to the
    # buildenv in finetuning
    # the second extraction is done to ensure that files from the archive
    # can't be modified/removed in finetuning

    outf.h2( "archive extract before finetuning" )

    if xml.has("archive"):
        with xml.archive_tmpfile() as fp:
            outf.do( 'tar xvfj "%s" -C "%s"' % (fp.name, targetfs.path) )

    outf.h2( "finetuning log" )
    outf.verbatim_start()

    index = cache.get_fileindex()
    mt_index = targetfs.mtime_snap()
    if xml.has("target/finetuning"):
        do_finetuning(xml, outf, buildenv, targetfs)
        #outf.print_raw( do_command( opt.finetuning ) )
        mt_index_post_fine = targetfs.mtime_snap()
    else:
        mt_index_post_fine = mt_index

    outf.verbatim_end()

    outf.h2( "archive extract after finetuning" )

    if xml.has("archive"):
        with xml.archive_tmpfile() as fp:
            outf.do( 'tar xvfj "%s" -C "%s"' % (fp.name, targetfs.path) )
        mt_index_post_arch = targetfs.mtime_snap()
    else:
        mt_index_post_arch = mt_index_post_fine

    outf.h2( "fileslist" )
    outf.table()

    tgt_pkg_list = set()

    for fpath, realpath in targetfs.walk_files():
        if index.has_key(fpath):
            pkg = index[fpath]
            tgt_pkg_list.add(pkg)
        else:
            pkg = "postinst generated"

        if mt_index_post_fine.has_key(fpath) and mt_index.has_key(fpath):
            if mt_index_post_fine[fpath] > mt_index[fpath]:
                pkg = "modified finetuning"
        if mt_index_post_fine.has_key(fpath):
            if mt_index_post_arch[fpath] > mt_index_post_fine[fpath]:
                pkg = "from archive"
            elif not mt_index.has_key(fpath):
                pkg = "added in finetuning"
        else:
            pkg = "added in archive"

        outf.printo( "|+%s+|%s" % (fpath,pkg) )

    outf.table()

    outf.h2( "Deleted Files" )
    outf.table()
    for fpath in mt_index.keys():
        if not mt_index_post_arch.has_key(fpath):
            if index.has_key(fpath):
                pkg = index[fpath]
            else:
                pkg = "postinst generated"
            outf.printo( "|+%s+|%s" % (fpath,pkg) )
    outf.table()

    outf.h2( "Target Package List" )
    outf.table()
    instpkgs = cache.get_installed_pkgs()
    pkgindex = {}
    for p in instpkgs:
        pkgindex[p.name] = p

    if xml.has("target/pkgversionlist"):
        targetfs.remove('etc/elbe_pkglist')
        f = targetfs.open('etc/elbe_pkglist', 'w')
    for pkg in tgt_pkg_list:
        p = pkgindex[pkg]
        outf.printo( "|%s|%s|%s|%s" % (p.name, p.installed_version, p.is_auto_installed, p.installed_md5) )
        if xml.has("target/pkgversionlist"):
            f.write ("%s %s %s\n" % (p.name, p.installed_version, p.installed_md5))
    outf.table()

    if xml.has("target/pkgversionlist"):
        f.close ()

