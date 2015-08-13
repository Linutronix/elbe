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

from elbepack.treeutils import etree
from elbepack.validate import validate_xml
from elbepack.xmldefaults import ElbeDefaults

from elbepack.version import elbe_version, is_devel

from base64 import standard_b64decode
from tempfile import NamedTemporaryFile

from urllib2 import urlopen, URLError

class ValidationError(Exception):
    def __init__(self, validation):
        Exception.__init__(self)
        self.validation = validation

    def __repr__(self):
        rep = "Elbe XML Validation Error\n"
        for v in self.validation:
            rep += (v+'\n')
        return rep

    def __str__(self):
        retval = ""
        for v in self.validation:
            retval += (v+'\n')
        return retval

class NoInitvmNode(Exception):
    pass

class ElbeXML(object):
    def __init__(self, fname, buildtype=None, skip_validate=False):
        if not skip_validate:
            validation = validate_xml (fname)
            if len (validation) != 0:
                raise ValidationError (validation)

        self.xml = etree( fname )
        self.prj = self.xml.node("/project")
        self.tgt = self.xml.node("/target")

        if buildtype:
            pass
        elif self.xml.has( "project/buildtype" ):
            buildtype = self.xml.text( "/project/buildtype" )
        else:
            buildtype = "nodefaults"
        self.defs = ElbeDefaults(buildtype)

        self.validate_apt_sources ()

    def text(self, txt, key=None):
        if key:
            return self.xml.text(txt, default=self.defs, key=key)
        else:
            return self.xml.text(txt)

    def has(self, path):
        return self.xml.has(path)

    def node(self, path):
        return self.xml.node(path)

    def is_cross (self, host_arch):

        target = self.text ("project/buildimage/arch", key="arch")

        if (host_arch == target):
            return False

        if ((host_arch == "amd64") and (target == "i386")):
            return False

        if ((host_arch == "armhf") and (target == "armel")):
            return False

        return True

    def get_primary_mirror (self, cdrompath):
        if self.prj.has("mirror/primary_host"):
            m = self.prj.node("mirror")

            mirror = m.text("primary_proto") + "://"
            mirror +=m.text("primary_host")  + "/"
            mirror +=m.text("primary_path")

        elif self.prj.has("mirror/cdrom") and cdrompath:
            mirror = "file://%s" % cdrompath

        return mirror.replace("LOCALMACHINE", "10.0.2.2")


    # XXX: maybe add cdrom path param ?
    def create_apt_sources_list (self):
        if self.prj is None:
            return "# No Project"

        if not self.prj.has("mirror") and not self.prj.has("mirror/cdrom"):
            return "# no mirrors configured"

        mirror = ""
        if self.prj.has("mirror/primary_host"):
            mirror += "deb " + self.get_primary_mirror (None)
            mirror += " " + self.prj.text("suite") + " main\n"

            if self.prj.has("mirror/url-list"):
                for url in self.prj.node("mirror/url-list"):
                    if url.has("binary"):
                        mirror += "deb " + url.text("binary").strip() + "\n"
                    if url.has("source"):
                        mirror += "deb-src "+url.text("source").strip()+"\n"

        if self.prj.has("mirror/cdrom"):
            mirror += "deb copy:///cdrom %s main added\n" % (self.prj.text("suite"))

        return mirror.replace("LOCALMACHINE", "10.0.2.2")

    def validate_apt_sources (self):
        slist = self.create_apt_sources_list ()
        sources_lines = slist.split ('\n')

        urls = []
        for l in sources_lines:
            if l.startswith ("deb "):
                lsplit = l.split (" ")
                urls.append ("%s/dists/%s/Release" % (lsplit[1], lsplit[2]))
            elif l.startswith ("deb-src "):
                lsplit = l.split (" ")
                urls.append ("%s/dists/%s/Release" % (lsplit[1], lsplit[2]))

        for u in urls:
            try:
                fp = urlopen (u)
                fp.read()
                fp.close()
            except URLError:
                raise ValidationError (["Repository %s can not be validated" % u])


    def get_target_packages(self):
        return [p.et.text for p in self.xml.node("/target/pkg-list")]

    def set_target_packages(self, pkglist):
        plist = self.xml.ensure_child("/target/pkg-list")
        plist.clear()
        for p in pkglist:
            pak = plist.append('pkg')
            pak.set_text( p )
            pak.et.tail = '\n'


    def get_buildenv_packages(self):
        retval = []
        if self.xml.has("./project/buildimage/pkg-list"):
            retval = [p.et.text for p in self.xml.node("project/buildimage/pkg-list")]

        return retval

    def clear_pkglist( self, name ):
        tree = self.xml.ensure_child( name )
        tree.clear()

    def append_pkg( self, aptpkg, name ):
        tree = self.xml.ensure_child( name )
        pak = tree.append( 'pkg' )
        pak.set_text( aptpkg.name )
        pak.et.tail = '\n'
        if aptpkg.installed_version is not None:
            pak.et.set( 'version', aptpkg.installed_version )
            pak.et.set( 'md5', aptpkg.installed_md5 )
        else:
            pak.et.set( 'version', aptpkg.candidate_version )
            pak.et.set( 'md5', aptpkg.candidate_md5 )

        if aptpkg.is_auto_installed:
            pak.et.set( 'auto', 'true' )
        else:
            pak.et.set( 'auto', 'false' )

    def clear_full_pkglist( self ):
        tree = self.xml.ensure_child( 'fullpkgs' )
        tree.clear()

    def clear_debootstrap_pkglist( self ):
        tree = self.xml.ensure_child( 'debootstrappkgs' )
        tree.clear()

    def clear_initvm_pkglist( self ):
        tree = self.xml.ensure_child( 'initvmpkgs' )
        tree.clear()

    def append_full_pkg( self, aptpkg ):
        self.append_pkg( aptpkg, 'fullpkgs' )

    def append_debootstrap_pkg( self, aptpkg ):
        self.append_pkg( aptpkg, 'debootstrappkgs' )

    def append_initvm_pkg( self, aptpkg ):
        self.append_pkg( aptpkg, 'initvmpkgs' )

    def archive_tmpfile( self ):
        fp = NamedTemporaryFile()
        fp.write( standard_b64decode( self.text("archive") ) )
        fp.file.flush()
        return fp

    def get_debootstrappkgs_from( self, other ):
        tree = self.xml.ensure_child( 'debootstrappkgs' )
        tree.clear()

        for e in other.node( 'debootstrappkgs' ):
            tree.append_treecopy( e )

    def get_initvmnode_from( self, other ):
        ivm = other.node( 'initvm' )
        if ivm is None:
            raise NoInitvmNode()

        tree = self.xml.ensure_child( 'initvm' )
        tree.clear()

        for e in ivm:
            tree.append_treecopy( e )

        self.xml.set_child_position( tree, 0 )

    def get_initvm_codename (self):
        if self.has ("initvm/suite"):
            return self.text ("initvm/suite")
        else:
            return None

    def set_cdrom_mirror (self, abspath):
        mirror = self.node("project/mirror")
        mirror.clear()
        cdrom = mirror.ensure_child("cdrom")
        cdrom.set_text( abspath )

    def dump_elbe_version (self):
        if is_devel:
            ver_text = elbe_version + '-devel'
        else:
            ver_text = elbe_version

        version = self.xml.ensure_child ('elbe_version')
        version.set_text (ver_text)

    def get_elbe_version (self):
        if self.has ('elbe_version'):
            return self.text ('elbe_version')
        else:
            return "no version"
