#!/usr/bin/env python
#
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

from treeutils import etree
from optparse import OptionParser
from subprocess import Popen, PIPE, STDOUT
from sets import Set
import datetime
import apt
import sys
import os

from version import elbe_version

def get_fileindex():

    cache = apt.cache.Cache( memonly=True )
    index = {}

    for p in cache:
        if p.is_installed:
            for f in p.installed_files:
                index[f] = p.name

    return index

def walk_files(dirname, exclude_dirs=[]):
    if dirname=="/":
        striplen = 0
    else:
        striplen = len(dirname)
    for dirpath, dirnames, filenames in os.walk(dirname):
        subpath = dirpath[striplen:]
        if len(subpath) == 0:
            subpath="/"

        deldirs = []
        for d in dirnames:
            dpath = os.path.join( subpath, d )
            if dpath in exclude_dirs:
                deldirs.append(d)

        for d in deldirs:
            dirnames.remove(d)

        for f in filenames:
            fpath = os.path.join( subpath, f )
            realpath = os.path.join( dirpath, f )
            yield fpath, realpath


def walk_dir(dirname, index, exclude_dirs=[]):

    for fpath, realpath in walk_files(dirname,exclude_dirs):
        if index.has_key(fpath):
            pkg = index[fpath]
        else:
            pkg = "no package"

        print pkg, fpath

def mtime_snap(dirname, exclude_dirs=[]):
    mtime_index = {}

    for fpath, realpath in walk_files(dirname,exclude_dirs):
        stat = os.lstat(realpath)
        mtime_index[fpath] = stat.st_mtime

    return mtime_index

def get_pkgs( kinitrd ):

    cache = apt.cache.Cache( memonly=True )

    pkgs = []
    for p in cache:
        if p.is_installed:
            pkgs.append( (p.name, p.installed.version, p.is_auto_installed, p.installed.md5))
        elif p.name == kinitrd:
            pkgs.append( (p.name, p.candidate.version, False, p.candidate.md5) )

    return pkgs


def append_pkg_elem( tree, name, version, auto, md5 ):
    pak = tree.append( 'pkg' )
    pak.set_text( name )
    pak.et.tail = '\n'
    pak.et.set( 'version', version )
    pak.et.set( 'md5', md5 )
    if auto:
        pak.et.set( 'auto', 'true' )
    else:
        pak.et.set( 'auto', 'false' )


def read_file( fname ):
    f = file( fname, "r" )
    d = f.read()
    f.close()
    return d

def do_command(cmd):
    p = Popen(cmd, shell=True, stdout=PIPE, stderr=STDOUT )
    output, stderr = p.communicate()
    return output


class asccidoclog(object):
    def __init__(self, fname):
        if os.path.isfile(fname):
            os.unlink(fname)
        self.fp = file(fname, "w")

    def printo(self, text=""):
        self.fp.write(text+"\n")

    def print_raw(self, text):
        self.fp.write(text)

    def h1(self, text):
        self.printo()
        self.printo(text)
        self.printo("="*len(text))
        self.printo()

    def h2(self, text):
        self.printo()
        self.printo(text)
        self.printo("-"*len(text))
        self.printo()

    def table(self):
        self.printo( "|=====================================" )

    def verbatim_start(self):
        self.printo( "------------------------------------------------------------------------------" )

    def verbatim_end(self):
        self.printo( "------------------------------------------------------------------------------" )
        self.printo()

def check_full_pkgs(pkgs, fullpkgs, errorname, kinitrd):
    elog = asccidoclog(errorname)

    elog.h1("ELBE Package validation")
    elog.h2("Package List validation")

    errors = 0
    cache = apt.cache.Cache( memonly=True )

    for name in [p.et.text for p in pkgs] + [kinitrd]:

        nomulti_name = name.split(":")[0]
        if not nomulti_name in cache:
            elog.printo( "- package %s does not exist" % nomulti_name )
            errors += 1
            continue

        cp = cache[nomulti_name]

        if not cp.installed and nomulti_name != kinitrd:
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

        if not name in cache:
            elog.printo( "- package %s does not exist" % name )
            errors += 1
            continue

        cp = cache[name]

        if not cp.installed:
            if name != kinitrd:
                elog.printo( "- package %s is not installed" % name )
                errors += 1
                continue
            else:
                cpi = cp.candidate
        else:
            cpi = cp.installed


        if cpi.version != ver:
            elog.printo( "- package %s version %s does not match installed version %s" % (name, ver,  cpi.version) )
            errors += 1
            continue

        if cpi.md5 != md5:
            elog.printo( "- package %s md5 %s does not match installed md5 %s" % (name, md5,  cpi.md5) )
            errors += 1

    for cp in cache:
        if cp.is_installed:
            if not pindex.has_key(cp.name):
                elog.printo( "additional package %s installed, that was not requested" % cp.name )
                errors += 1

    if errors == 0:
        elog.printo( "No Errors found" )

def run_command( argv ):
    oparser = OptionParser(usage="usage: %prog dump [options] <xmlfile>")

    oparser.add_option( "-f", "--finetuning", dest="finetuning",
                        help="filename of finetuning script" )
    oparser.add_option( "-t", "--target", dest="target",
                        help="directoryname of target" )
    oparser.add_option( "-a", "--archive", dest="archive",
                        help="filename of archive" )
    oparser.add_option( "-o", "--output", dest="output",
                        help="name of logfile" )
    oparser.add_option( "-n", "--name", dest="name",
                        help="name of the project (included in the report)" )
    oparser.add_option( "-v", "--validation", dest="validation",
                        help="name of the validation logfile" )
    oparser.add_option( "-k", "--kinitrd", dest="kinitrd",
                        help="name of the kinitrd package" )
    (opt,args) = oparser.parse_args(argv)

    if len(args) != 1:
       print "Wrong number of arguments"
       oparser.print_help()
       sys.exit(20)

    xml = etree( args[0] )

    if opt.validation:
        pkgs = xml.node("/target/pkg-list")
        if xml.has("fullpkgs"):
            check_full_pkgs(pkgs, xml.node("/fullpkgs"), opt.validation, opt.kinitrd)
        else:
            check_full_pkgs(pkgs, None, opt.validation, opt.kinitrd)

    paktree = xml.ensure_child( 'fullpkgs' )
    paktree.clear()

    curr_pkgs = get_pkgs( opt.kinitrd )
    for p in curr_pkgs:
        append_pkg_elem( paktree, p[0], p[1], p[2], p[3] )

    sources_list = xml.ensure_child( 'sources_list' )
    slist = read_file("/etc/apt/sources.list")
    sources_list.set_text( slist )

    try:
        preferences = xml.ensure_child( 'apt_prefs' )
        prefs = read_file("/etc/apt/preferences")
        preferences.set_text(prefs)
    except:
        print "no /etc/apt/preferences on system"
        prefs = ""

    buildv = xml.ensure_child( 'elbe_version' )
    buildv.set_text(elbe_version)

    xml.write( args[0] )

    if not opt.output:
        return 0
    if not opt.target:
        return 0

    outf = asccidoclog(opt.output)

    if opt.name:
        outf.h1( "ELBE Report for Project "+opt.name )
    else:
        outf.h1( "ELBE Report" )

    outf.printo( "report timestamp: "+datetime.datetime.now().strftime("%Y%m%d-%H%M%S") )

    outf.h2( "Apt Sources dump" )
    outf.verbatim_start()
    outf.print_raw(slist)
    outf.verbatim_end()

    outf.h2( "Apt Preferences dump" )
    outf.verbatim_start()
    outf.print_raw(prefs)
    outf.verbatim_end()

    outf.h2( "Installed Packages List" )
    outf.table()
    cache = apt.Cache(memonly=True)
    for p in cache:
        if p.is_installed:
            orig = p.installed.origins[0].site
            outf.printo( "|%s|%s|%s" % (p.name, p.installed.version, orig) )
    outf.table()

    # archive extraction is done before and after finetuning the first
    # extraction is needed that the files can be used (copied/moved to the
    # buildenv in finetuning
    # the second extraction is done to ensure that files from the archive
    # can't be modified/removed in finetuning

    outf.h2( "archive extract before finetuning" )

    if opt.archive:
        outf.verbatim_start()
        outf.print_raw( do_command( 'tar xvfj "%s" -C "%s"' % (opt.archive, opt.target) ) )
        outf.verbatim_end()

    outf.h2( "finetuning log" )
    outf.verbatim_start()

    index = get_fileindex()
    mt_index = mtime_snap( opt.target )
    if opt.finetuning:
        outf.print_raw( do_command( opt.finetuning ) )
        mt_index_post_fine = mtime_snap( opt.target )
    else:
        mt_index_post_fine = mt_index

    outf.verbatim_end()

    outf.h2( "archive extract after finetuning" )

    outf.verbatim_start()

    if opt.archive:
        outf.print_raw( do_command( 'tar xvfj "%s" -C "%s"' % (opt.archive, opt.target) ) )
        mt_index_post_arch = mtime_snap( opt.target )
    else:
        mt_index_post_arch = mt_index_post_fine

    outf.verbatim_end()

    outf.h2( "fileslist" )
    outf.table()

    tgt_pkg_list = Set()

    for fpath, realpath in walk_files(opt.target):
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
    cache = apt.Cache(memonly=True)
    if xml.has("target/pkgversionlist"):
        os.remove('/target/etc/elbe_pkglist')
        f = open('/target/etc/elbe_pkglist', 'w')
    for pkg in tgt_pkg_list:
        p = cache[pkg]
        outf.printo( "|%s|%s|%s|%s" % (p.name, p.installed.version, p.is_auto_installed, p.installed.md5) )
        if xml.has("target/pkgversionlist"):
            f.write ("%s %s %s\n" % (p.name, p.installed.version, p.installed.md5))
    outf.table()

    if xml.has("target/pkgversionlist"):
        f.close ()

if __name__ == "__main__":
    run_command( sys.argv[1:] )
