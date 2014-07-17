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
from elbepack.filesystem import Filesystem
from elbepack.pkgutils import get_dsc_size



class RepoBase(object):
    def __init__( self, path, log, arch, codename, origin, description, components="main", maxsize=None ):

        self.vol_path = path
        self.volume_count = 0

        self.log = log
        self.codename = codename
        self.arch = arch
        self.components = components
        self.origin = origin
        self.description = description
        self.maxsize = maxsize

        self.fs = self.get_volume_fs(self.volume_count)

        self.gen_repo_conf()

    def get_volume_fs( self, volume ):
        if self.maxsize:
            volname = os.path.join( self.vol_path, "vol%02d" % volume )
            return Filesystem(volname)
        else:
            return Filesystem(self.vol_path)

    def new_repo_volume( self ):
        self.volume_count += 1
        self.fs = self.get_volume_fs(self.volume_count)
        self.gen_repo_conf()

    def gen_repo_conf( self ):
        self.fs.mkdir_p( "conf" )
        fp = self.fs.open( "conf/distributions", "w")

        fp.write( "Origin: " + self.origin + "\n" )
        fp.write( "Label: " + self.origin + "\n" )
        fp.write( "Suite: " + codename2suite[ self.codename ] + "\n" )
        fp.write( "Codename: " + self.codename + "\n" )
        fp.write( "Architectures: " + self.arch + "\n" )
        fp.write( "Components: " + self.components + "\n" )
        fp.write( "Description: " + self.description + "\n" )

        fp.close()

    def includedeb( self, path, component="main"):
        if self.maxsize:
            new_size = self.fs.disk_usage("") + os.path.getsize( path )
            if new_size > self.maxsize:
                self.new_repo_volume()

        self.log.do( "reprepro --basedir " + self.fs.path + " -C " + component + " includedeb " + self.codename + " " + path )

    def includedsc( self, path, component="main"):
        if self.maxsize:
            new_size = self.fs.disk_usage("") + get_dsc_size( path )
            if new_size > self.maxsize:
                self.new_repo_volume()

        if self.maxsize and (self.fs.disk_usage("") > self.maxsize):
            self.new_repo_volume()

        self.log.do( "reprepro --basedir " + self.fs.path + " -C " + component + " -P normal -S misc includedsc " + self.codename + " " + path ) 

    def buildiso( self, fname ):
        if self.volume_count == 0:
            self.log.do( "genisoimage -o %s -J -R %s" % (fname, self.fs.path) )
        else:
            for i in range(self.volume_count+1):
                volfs = self.get_volume_fs(i)
                newname = fname + ("%02d" % i)
                self.log.do( "genisoimage -o %s -J -R %s" % (newname, volfs.path) )



class UpdateRepo(RepoBase):
    def __init__( self, xml, path, log ):
        self.xml  = xml

        arch = xml.text("project/arch", key="arch" )
        codename = xml.text("project/suite")

        RepoBase.__init__( self, path, log, arch, codename, "Update", "Update", "main" )

class CdromBinRepo(RepoBase):
    def __init__( self, xml, path, log, maxsize ):
        self.xml  = xml

        arch = xml.text("project/arch", key="arch" )
        codename = xml.text("project/suite")

        RepoBase.__init__( self, path, log, arch, codename, "Elbe", "Elbe Binary Cdrom Repo", "main added", maxsize )

class CdromSrcRepo(RepoBase):
    def __init__( self, codename, path, log, maxsize ):
        RepoBase.__init__( self, path, log, "source", codename, "Elbe", "Elbe Source Cdrom Repo", "main", maxsize )


class ToolchainRepo(RepoBase):
    def __init__( self, arch, codename, path, log):
        RepoBase.__init__( self, path, log, arch, codename, "toolchain", "Toolchain binary packages Repo", "main" )
