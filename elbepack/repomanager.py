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

import os
from elbepack.debianreleases import codename2suite


class RepoBase(object):
    def __init__( self, path, log, arch, codename, origin, description, components="main" ):

        self.path = path
        self.log = log
        self.codename = codename
        self.arch = arch
        self.components = components
        self.origin = origin
        self.description = description


        repoconfdir = os.path.join( path, "conf" )

        self.log.do( 'mkdir -p %s' % repoconfdir )

        repoconf = os.path.join( repoconfdir, "distributions" )
        fp = open(repoconf, "w")

        fp.write( "Origin: " + self.origin + "\n" )
        fp.write( "Label: " + self.origin + "\n" )
        fp.write( "Suite: " + codename2suite[ self.codename ] + "\n" )
        fp.write( "Codename: " + self.codename + "\n" )
        fp.write( "Architectures: " + self.arch + "\n" )
        fp.write( "Components: " + self.components + "\n" )
        fp.write( "Description: " + self.description + "\n" )

        fp.close()

    def includedeb( self, path, component="main"):
        self.log.do( "reprepro --basedir " + self.path + " -C " + component + " includedeb " + self.codename + " " + path )
    
    def includedsc( self, path, component="main"):
        self.log.do( "reprepro --basedir " + self.path + " -C " + component + " -P normal -S misc includedsc " + self.codename + " " + path ) 

    def buildiso( self, fname ):
        self.log.do( "genisoimage -o %s -J -R %s" % (fname, self.path) )


class UpdateRepo(RepoBase):
    def __init__( self, xml, path, log ):
        self.xml  = xml

        arch = xml.text("project/arch", key="arch" )
        codename = xml.text("project/suite")

        RepoBase.__init__( self, path, log, arch, codename, "Update", "Update", "main" )

class CdromBinRepo(RepoBase):
    def __init__( self, xml, path, log ):
        self.xml  = xml

        arch = xml.text("project/arch", key="arch" )
        codename = xml.text("project/suite")

        RepoBase.__init__( self, path, log, arch, codename, "Elbe", "Elbe Binary Cdrom Repo", "main added" )

class CdromSrcRepo(RepoBase):
    def __init__( self, codename, path, log ):
        RepoBase.__init__( self, path, log, "source", codename, "Elbe", "Elbe Source Cdrom Repo", "main" )

