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

from shutil import rmtree, copyfile, copytree

from elbepack.elbexml import ElbeXML
from elbepack.dump import dump_fullpkgs
from elbepack.ziparchives import create_zip_archive
from elbepack.repomanager import UpdateRepo

class MissingData(Exception):
    def __init__ (self, message):
        Exception.__init__( self, message )

def inlucdedir (destination, directory, source, mode=None):
    dst = destination + '/' + directory
    copytree (source, dst)
    if mode:
        for dp, dn, fn in os.walk(dst):
            for f in fn:
                p = os.path.join (dp, f)
                os.chmod (p, mode)

def gen_update_pkg (project, xml_filename, upd_filename,
        override_buildtype = None, skip_validate = False, debug = False,
        cmd_dir = None, cfg_dir=None):

    if xml_filename:
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

    if xml_filename:
        repodir = os.path.join(update, "repo" )

        repo = UpdateRepo( xml, repodir, project.log )

        for fname in fnamelist:
            path = os.path.join( project.chrootpath, "var/cache/apt/archives", fname )
            repo.includedeb( path )

        repo.finalize ()

        dump_fullpkgs(project.xml, project.buildenv.rfs, cache)

        project.xml.xml.write( os.path.join( update, "new.xml" ) )
        os.system( "cp %s %s" % (xml_filename, os.path.join( update, "base.xml" )) )
    else:
        os.system( "cp source.xml update/new.xml")

    if project.presh_file:
        copyfile (project.presh_file, update + '/pre.sh')
        os.chmod (update + '/pre.sh', 0o755)

    if project.postsh_file:
        copyfile (project.postsh_file, update + '/post.sh')
        os.chmod (update + '/post.sh', 0o755)

    if cmd_dir:
        inlucdedir (update, 'cmd', cmd_dir, mode=0o755)

    if cfg_dir:
        inlucdedir (update, 'conf', cfg_dir)

    create_zip_archive( upd_filename, update, "." )

    if project.postbuild_file:
        project.log.h2 ("postbuild script")
        project.log.do (project.postbuild_file+' "%s %s %s"'%(
            upd_filename,
            project.xml.text ("project/version"),
            project.xml.text ("project/name")),
          allow_fail=True)
