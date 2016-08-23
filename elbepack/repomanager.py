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
from debian.deb822 import Deb822

class RepoAttributes(object):
    def __init__ (self, codename, arch, components,
            mirror='http://ftp.debian.org/debian' ):
        self.codename = codename
        if type (arch) is str:
            self.arch = set ([arch])
        else:
            self.arch = set (arch)

        if type(components) is str:
            self.components = set ([components])
        else:
            self.components = set (components)

        self.mirror = mirror

    def __add__ (self, other):
        """ Over simplistic Add implementation only useful for
            our current implementation"""

        if other.codename != self.codename:
            return [self, other]
        else:
            assert self.mirror == other.mirror
            ret_arch = self.arch.union (other.arch)
            ret_comp = self.components.union (other.components)

            return [ RepoAttributes (self.codename, ret_arch, ret_comp, self.mirror) ]


class RepoBase(object):
    def __init__( self, path, log, init_attr, repo_attr, origin, description, maxsize=None):

        self.vol_path = path
        self.volume_count = 0

        self.log = log
        self.init_attr = init_attr
        self.repo_attr = repo_attr

        if init_attr is not None and repo_attr is not None:
            self.attrs = init_attr + repo_attr
        elif repo_attr is not None:
            self.attrs = [repo_attr]
        elif init_attr is not None:
            self.attrs = [init_attr]

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

        need_update = False

        for att in self.attrs:
            fp.write( "Origin: " + self.origin + "\n" )
            fp.write( "Label: " + self.origin + "\n" )
            fp.write( "Suite: " + codename2suite[ att.codename ] + "\n" )
            fp.write( "Codename: " + att.codename + "\n" )
            fp.write( "Architectures: " + " ".join (att.arch) + "\n" )
            fp.write( "Components: " + " ".join (att.components.difference (set (["main/debian-installer"]))) + "\n" )
            fp.write( "UDebComponents: " + " ".join (att.components.difference (set (["main/debian-installer"]))) + "\n" )
            fp.write( "Description: " + self.description + "\n" )

            if 'main/debian-installer' in att.components:
                fp.write( "Update: di\n" )

                ufp = self.fs.open( "conf/updates", "w" )

                ufp.write( "Name: di\n" )
                ufp.write( "Method: " + att.mirror + "\n" )
                ufp.write( "VerifyRelease: blindtrust\n" )
                ufp.write( "Components: \n" )
                ufp.write( "GetInRelease: no\n" )
                # It would be nicer, to use this
                # ufp.write( "Architectures: " + " ".join (att.arch) + "\n" )
                # But we end up with 'armel amd64' sometimes.
                # So lets just use the init_attr...
                if self.init_attr:
                    ufp.write( "Architectures: " + " ".join (self.init_attr.arch) + "\n" )
                else:
                    ufp.write( "Architectures: " + " ".join (att.arch) + "\n" )

                ufp.write ( "UDebComponents: main>main\n" )
                ufp.close()

                need_update = True

            fp.write( "\n" )
        fp.close()

        if need_update:
            self.log.do( 'reprepro --export=force --basedir "' + self.fs.path + '" update' )
        else:
            self.log.do( 'reprepro --basedir "' + self.fs.path + '" export ' + att.codename )

    def finalize( self ):
        for att in self.attrs:
            self.log.do( 'reprepro --basedir "' + self.fs.path + '" export ' + att.codename )

    def _includedeb( self, path, codename, component):
        if self.maxsize:
            new_size = self.fs.disk_usage("") + os.path.getsize( path )
            if new_size > self.maxsize:
                self.new_repo_volume()

        self.log.do( 'reprepro --keepunreferencedfiles --export=never --basedir "' + self.fs.path + '" -C ' + component + ' includedeb ' + codename + ' ' + path )

    def includedeb (self, path, component="main"):
        self._includedeb (path, self.repo_attr.codename, component)

    def include_init_deb (self, path, component="main"):
        self._includedeb (path, self.init_attr.codename, component)

    def _include( self, path, codename, component):
        self.log.do( 'reprepro --ignore=wrongdistribution --keepunreferencedfiles --export=never --basedir "' + self.fs.path  + '" -C ' + component + ' -P normal -S misc include ' + codename + ' ' + path )

    def _remove( self, path, codename, component):
        for p in Deb822.iter_paragraphs(file(path)):
            if 'Source' in p:
                self.log.do( "reprepro --basedir %s removesrc %s %s" % (self.fs.path, codename, p['Source']))
            elif 'Package' in p:
                self.log.do( "reprepro --basedir %s remove %s %s" % (self.fs.path, codename, p['Package']))

    def _includedsc( self, path, codename, component):
        if self.maxsize:
            new_size = self.fs.disk_usage("") + get_dsc_size( path )
            if new_size > self.maxsize:
                self.new_repo_volume()

        if self.maxsize and (self.fs.disk_usage("") > self.maxsize):
            self.new_repo_volume()

        self.log.do( 'reprepro --keepunreferencedfiles --export=never --basedir "' + self.fs.path  + '" -C ' + component + ' -P normal -S misc includedsc ' + codename + ' ' + path )

    def includedsc( self, path, component="main"):
        self._includedsc (path, self.repo_attr.codename, component)

    def include( self, path, component="main"):
        self._include (path, self.repo_attr.codename, component)

    def remove( self, path, component="main"):
        self._remove (path, self.repo_attr.codename, component)

    def include_init_dsc( self, path, component="main"):
        self._includedsc (path, self.init_attr.codename, component)

    def buildiso( self, fname ):
        files = []
        if self.volume_count == 0:
            new_path = '"' + self.fs.path + '"'
            self.log.do( "genisoimage -o %s -J -joliet-long -R %s" % (fname, new_path) )
            files.append (fname)
        else:
            for i in range(self.volume_count+1):
                volfs = self.get_volume_fs(i)
                newname = fname + ("%02d" % i)
                self.log.do( "genisoimage -o %s -J -joliet-long -R %s" % (newname,
                                                             volfs.path) )
                files.append (newname)

        return files


class UpdateRepo(RepoBase):
    def __init__( self, xml, path, log ):
        self.xml  = xml

        arch = xml.text("project/arch", key="arch" )
        codename = xml.text("project/suite")

        repo_attrs = RepoAttributes (codename, arch, "main")

        RepoBase.__init__( self,
                           path,
                           log,
                           None,
                           repo_attrs,
                           "Update",
                           "Update")

class CdromInitRepo(RepoBase):
    def __init__( self, arch, init_codename, path, log, maxsize, mirror='http://ftp.debian.org/debian'  ):

        init_attrs = RepoAttributes (init_codename, "amd64", ["main", "main/debian-installer"], mirror)

        RepoBase.__init__( self,
                           path,
                           log,
                           None,
                           init_attrs,
                           "Elbe",
                           "Elbe InitVM Cdrom Repo",
                           maxsize )

class CdromBinRepo(RepoBase):
    def __init__( self, arch, codename, init_codename, path, log, maxsize, mirror='http://ftp.debian.org/debian'  ):

        repo_attrs = RepoAttributes (codename, arch, ["main", "added"], mirror)
        if init_codename is not None:
            init_attrs = RepoAttributes (init_codename, "amd64", ["main", "main/debian-installer"], mirror)
        else:
            init_attrs = None

        RepoBase.__init__( self,
                           path,
                           log,
                           init_attrs,
                           repo_attrs,
                           "Elbe",
                           "Elbe Binary Cdrom Repo",
                           maxsize )


class CdromSrcRepo(RepoBase):
    def __init__( self, codename, init_codename, path, log, maxsize ):
        repo_attrs = RepoAttributes (codename, "source", ["main", "added"])
        if init_codename is not None:
            init_attrs = RepoAttributes (init_codename, "source", ["main", "main/debian-installer"])
        else:
            init_attrs = None

        RepoBase.__init__( self,
                           path,
                           log,
                           init_attrs,
                           repo_attrs,
                           "Elbe",
                           "Elbe Source Cdrom Repo",
                           maxsize)


class ToolchainRepo(RepoBase):
    def __init__( self, arch, codename, path, log):
        repo_attrs = RepoAttributes (codename, arch, "main")
        RepoBase.__init__( self,
                           path,
                           log,
                           None,
                           repo_attrs,
                           "toolchain",
                           "Toolchain binary packages Repo" )

class ProjectRepo(RepoBase):
    def __init__( self, arch, codename, path, log):
        repo_attrs = RepoAttributes (codename, arch + ' source', "main")
        RepoBase.__init__( self,
                           path,
                           log,
                           None,
                           repo_attrs,
                           "Local",
                           "Self build packages Repo" )
