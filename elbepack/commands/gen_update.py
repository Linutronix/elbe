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

from optparse import OptionParser
import sys
import os

from elbepack.elbexml import ElbeXML, ValidationError
from elbepack.rpcaptcache import get_rpcaptcache
from elbepack.filesystem import BuildImgFs
from elbepack.dump import dump_fullpkgs

from elbepack.ziparchives import create_zip_archive
from elbepack.repomanager import Repo

def run_command( argv ):
    oparser = OptionParser(usage="usage: %prog gen_update [options] <xmlfile>")
    oparser.add_option( "-t", "--target", dest="target",
                        help="directoryname of target" )
    oparser.add_option( "-n", "--name", dest="name",
                        help="name of the project (included in the report)" )
    oparser.add_option( "--skip-validation", action="store_true",
                        dest="skip_validation", default=False,
                        help="Skip xml schema validation" )
    oparser.add_option( "--buildtype", dest="buildtype",
                        help="Override the buildtype" )
    oparser.add_option( "--debug", action="store_true", dest="debug",
                        default=False,
                        help="Enable various features to debug the build" )

    (opt,args) = oparser.parse_args(argv)

    if len(args) != 1:
        print "wrong number of arguments"
        oparser.print_help()
        sys.exit(20)

    if not opt.target:
        print "No target specified"
        sys.exit(20)

    opt.target = os.path.abspath(opt.target)

    if opt.buildtype:
        buildtype = opt.buildtype
    else:
        buildtype = None

    try:
        xml = ElbeXML( args[0], buildtype=buildtype, skip_validate=opt.skip_validation )
    except ValidationError:
        print "xml validation failed. Bailing out"
        sys.exit(20)

    if not xml.has("fullpkgs"):
        print "Xml does not have fullpkgs list"
        sys.exit(20)

    sourcexml = os.path.join(opt.target, 'source.xml')
    try:
        sxml = ElbeXML( sourcexml, buildtype=buildtype, skip_validate=opt.skip_validation )
    except ValidationError:
        print "xml validation failed. Bailing out"
        sys.exit(20)

    if not sxml.has("fullpkgs"):
        print "Source Xml does not have fullpkgs list"
        sys.exit(20)

    chroot = os.path.join(opt.target, "chroot")

    buildrfs = BuildImgFs(chroot)

    arch = xml.text("project/arch", key="arch" )
    cache = get_rpcaptcache( buildrfs, "aptcache.log", arch )


    instpkgs  = cache.get_installed_pkgs()
    instindex = {}

    for p in instpkgs:
        instindex[p.name] = p

    xmlpkgs = xml.node("/fullpkgs")
    xmlindex = {}

    fnamelist = []

    for p in xmlpkgs:
        name = p.et.text
        ver  = p.et.get('version')
        md5  = p.et.get('md5')

        xmlindex[name] = p
    
        if not name in instindex:
            print "package removed: " + name
            continue

        ipkg = instindex[name]
        comp = cache.compare_versions(ipkg.installed_version, ver)

        pfname = ipkg.name + '_' + ipkg.installed_version.replace( ':', '%3a' ) + '_' + ipkg.architecture + '.deb'

        if comp == 0:
            print "package ok: " + name + "-" + ipkg.installed_version
            if opt.debug:
                fnamelist.append( pfname )
            continue

        if comp > 0:
            pfname = cache.get_filename( name )
            print "package upgrade: " + pfname
            fnamelist.append( pfname )
        else:
            print "package downgrade: " + name + "-" + ipkg.installed_version

    for p in instpkgs:
        if p.name in xmlindex:
            continue

        print "package new installed " + p.name
        pfname = p.name + '_' + p.installed_version.replace( ':', '%3a' ) + '_' + p.architecture + '.deb'
        fnamelist.append( pfname )


    update = os.path.join(opt.target, "update")
    os.system( 'mkdir -p %s' % update )

    repodir = os.path.join(update, "repo" )

    repo = Repo( xml, repodir )

    for fname in fnamelist:
        path = os.path.join( chroot, "var/cache/apt/archives", fname )
        repo.includedeb( path )


    dump_fullpkgs(sxml, buildrfs, cache)

    sxml.xml.write( os.path.join( update, "new.xml" ) )
    os.system( "cp %s %s" % (args[0], os.path.join( update, "base.xml" )) )

    zipfilename = os.path.join( opt.target, "%s_%s.upd" %
        (xml.text ("/project/name"), xml.text ("/project/version")) )

    create_zip_archive( zipfilename, update, "." )
