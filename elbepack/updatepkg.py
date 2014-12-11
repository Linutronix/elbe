#!/usr/bin/env python
#
# ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (C) 2013, 2014  Linutronix GmbH
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

import os

from shutil import rmtree, copyfileobj

from elbepack.elbexml import ElbeXML
from elbepack.dump import dump_fullpkgs
from elbepack.ziparchives import create_zip_archive
from elbepack.repomanager import UpdateRepo

class MissingData(Exception):
    def __init__ (self, message):
        Exception.__init__( self, message )

def gen_update_pkg (project, xml_filename, upd_filename,
        override_buildtype = None, skip_validate = False, debug = False):
    xml = ElbeXML( xml_filename, buildtype=override_buildtype,
            skip_validate=skip_validate )

    if not xml.has("fullpkgs"):
        raise MissingData("Xml does not have fullpkgs list")

    if not project.xml.has("fullpkgs"):
        raise MissingData("Source Xml does not have fullpkgs list")

    if not project.buildenv.rfs:
        raise MissingData("Target does not have a build environment")

    cache = project.get_rpcaptcache()

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

        pfname = ipkg.installed_deb

        if comp == 0:
            print "package ok: " + name + "-" + ipkg.installed_version
            if debug:
                fnamelist.append( pfname )
            continue

        if comp > 0:
            print "package upgrade: " + pfname
            fnamelist.append( pfname )
        else:
            print "package downgrade: " + name + "-" + ipkg.installed_version

    for p in instpkgs:
        if p.name in xmlindex:
            continue

        print "package new installed " + p.name
        pfname = p.installed_deb
        fnamelist.append( pfname )


    update = os.path.join(project.builddir, "update")

    if os.path.exists( update ):
        rmtree( update )

    os.system( 'mkdir -p %s' % update )

    repodir = os.path.join(update, "repo" )

    repo = UpdateRepo( xml, repodir, project.log )

    for fname in fnamelist:
        path = os.path.join( project.chrootpath, "var/cache/apt/archives", fname )
        repo.includedeb( path )


    dump_fullpkgs(project.xml, project.buildenv.rfs, cache)

    project.xml.xml.write( os.path.join( update, "new.xml" ) )
    os.system( "cp %s %s" % (xml_filename, os.path.join( update, "base.xml" )) )

    if project.presh_file:
        with open (update + '/pre.sh', 'w') as presh:
            copyfileobj (project.presh_file, presh)
        os.chmod (update + '/pre.sh', 0755)

    if project.postsh_file:
        with open (update + '/post.sh', 'w') as postsh:
            copyfileobj (project.postsh_file, postsh)
        os.chmod (update + '/post.sh', 0755)

    create_zip_archive( upd_filename, update, "." )
