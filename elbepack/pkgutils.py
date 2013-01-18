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



import sys
import os

from elbepack.treeutils import etree
from elbepack.validate import validate_xml
from elbepack import virtapt

from tempfile import mkdtemp

def get_sources_list( xml ):

    prj = xml.node("/project")
    suite = prj.text("suite")

    slist = ""
    if prj.has("mirror/primary_host"):
        mirror = "%s://%s/%s" % ( prj.text("mirror/primary_proto"), prj.text("mirror/primary_host"), prj.text("mirror/primary_path") )
        slist += "deb %s %s main\n" % (mirror, suite)
        slist += "deb-src %s %s main\n" % (mirror, suite)

    if prj.has("mirror/cdrom"):
        tmpdir = mkdtemp()
        kinitrd = prj.text("buildimage/kinitrd")
        os.system( '7z x -o%s "%s" pool/main/%s/%s dists' % (tmpdir, prj.text("mirror/cdrom"), kinitrd[0], kinitrd) )
        slist += "deb file://%s %s main\n" % (tmpdir,suite)

    if prj.node("mirror/url-list"):
        for n in prj.node("mirror/url-list"):
            slist += "deb %s\n" % n.text("binary").strip()

    return slist

def get_initrd_pkg( xml ):
    prj = xml.node("/project")
    initrdname = prj.text("buildimage/kinitrd")

    return initrdname

def get_initrd_uri( xml ):

    arch  = xml.text("project/buildimage/arch")
    suite = xml.text("project/suite")

    name  = xml.text("project/name")
    apt_sources = get_sources_list(xml)

    target_pkg = get_initrd_pkg(xml)

    v = virtapt.VirtApt( name, arch, suite, apt_sources, "" )
    d = virtapt.apt_pkg.DepCache(v.cache)

    pkg = v.cache[target_pkg]

    c=d.get_candidate_ver(pkg)
    x=v.source.find_index(c.file_list[0][0])

    r=virtapt.apt_pkg.PackageRecords(v.cache)
    r.lookup(c.file_list[0])
    uri = x.archive_uri(r.filename)





    return uri



def copy_kinitrd( xml, target_dir ):
    prj = xml.node("/project")
    uri = get_initrd_uri(xml)

    tmpdir = mkdtemp()

    if uri.startswith("file://"):
        os.system( 'cp "%s" "%s"' % ( uri[len("file://"):], os.path.join(tmpdir, "pkg.deb") ) )
    else:
        os.system( 'wget -O "%s" "%s"' % ( os.path.join(tmpdir, "pkg.deb"), uri ) )
    os.system( 'dpkg -x "%s" "%s"' % ( os.path.join(tmpdir, "pkg.deb"), tmpdir ) )

    if prj.has("mirror/cdrom"):
        os.system( 'cp "%s" "%s"' % ( os.path.join( tmpdir, 'opt', 'elbe', 'initrd', 'initrd-cdrom.gz' ), os.path.join(target_dir, "initrd.gz") ) )
    else:
        os.system( 'cp "%s" "%s"' % ( os.path.join( tmpdir, 'opt', 'elbe', 'initrd', 'initrd.gz' ), os.path.join(target_dir, "initrd.gz") ) )
    os.system( 'cp "%s" "%s"' % ( os.path.join( tmpdir, 'opt', 'elbe', 'initrd', 'vmlinuz' ), os.path.join(target_dir, "vmlinuz") ) )

    os.system( 'rm -r "%s"' % tmpdir )

