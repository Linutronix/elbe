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

from tempfile import mkdtemp
import urllib2

try:
    from elbepack import virtapt
except ImportError:
    print "WARNING - python-apt not available: if there are multiple versions of"
    print " kinitrd packages on the mirror(s) elbe selects the first package it"
    print " has found. There is no guarantee that the latest package is used."
    print " To ensure this, the python-apt package needs to be installed."
    import urllib2


def get_sources_list( xml, defs ):

    prj = xml.node("/project")
    suite = prj.text("suite")

    slist = ""
    if prj.has("mirror/primary_host"):
        mirror = "%s://%s/%s" % ( prj.text("mirror/primary_proto"), prj.text("mirror/primary_host"), prj.text("mirror/primary_path") )
        slist += "deb %s %s main\n" % (mirror, suite)
        slist += "deb-src %s %s main\n" % (mirror, suite)

    if prj.has("mirror/cdrom"):
        tmpdir = mkdtemp()
        kinitrd = prj.text("buildimage/kinitrd", default=defs, key="kinitrd")
        os.system( '7z x -o%s "%s" pool/main/%s/%s dists' % (tmpdir, prj.text("mirror/cdrom"), kinitrd[0], kinitrd) )
        slist += "deb file://%s %s main\n" % (tmpdir,suite)

    if prj.node("mirror/url-list"):
        for n in prj.node("mirror/url-list"):
            if n.has("binary"):
                tmp = n.text("binary").replace("LOCALMACHINE", "localhost")
                slist += "deb %s\n" % tmp.strip()
            if n.has("source"):
                tmp = n.text("source").replace("LOCALMACHINE", "localhost")
                slist += "deb-src %s\n" % tmp.strip()

    return slist

def get_initrd_pkg( xml, defs ):
    prj = xml.node("/project")
    initrdname = prj.text("buildimage/kinitrd", default=defs, key="kinitrd")

    return initrdname

def get_url ( xml, arch, suite, target_pkg, mirror ):
    packages = urllib2.urlopen("%s/dists/%s/main/binary-%s/Packages" %
      (mirror.replace("LOCALMACHINE", "localhost"), suite, arch))

    packages = packages.readlines()
    packages = filter( lambda x: x.startswith( "Filename" ), packages )
    packages = filter( lambda x: x.find( target_pkg ) != -1, packages )

    try:
        tmp = packages.pop()
        urla = tmp.split()
        url = "%s/%s" % (mirror.replace("LOCALMACHINE", "localhost"), urla[1])
    except:
        url = ""

    return url

def get_initrd_uri( xml, defs, arch ):
    if arch == "default":
        arch  = xml.text("project/buildimage/arch", default=defs, key="arch")
    suite = xml.text("project/suite")

    name  = xml.text("project/name", default=defs, key="name")
    apt_sources = get_sources_list(xml, defs)

    target_pkg = get_initrd_pkg(xml, defs)

    try:
        v = virtapt.VirtApt( name, arch, suite, apt_sources, "" )
        d = virtapt.apt_pkg.DepCache(v.cache)

        pkg = v.cache[target_pkg]

        c=d.get_candidate_ver(pkg)
        x=v.source.find_index(c.file_list[0][0])

        r=virtapt.apt_pkg.PackageRecords(v.cache)
        r.lookup(c.file_list[0])
        uri = x.archive_uri(r.filename)
        return uri
    except:
        url = "%s://%s/%s" % (xml.text("project/mirror/primary_proto"),
          xml.text("project/mirror/primary_host"),
          xml.text("project/mirror/primary_path") )
        pkg = get_url ( xml, arch, suite, target_pkg, url )

        if pkg:
            return pkg

        for n in xml.node("project/mirror/url-list"):
            url = n.text("binary")
            urla = url.split()
            pkg = get_url ( xml, arch, suite, target_pkg,
              urla[0].replace("BUILDHOST", "localhost") )

            if pkg:
                return pkg

    return ""



def copy_kinitrd( xml, target_dir, defs, arch="default" ):
    prj = xml.node("/project")
    uri = get_initrd_uri(xml, defs, arch)

    tmpdir = mkdtemp()

    if uri.startswith("file://"):
        os.system( 'cp "%s" "%s"' % ( uri[len("file://"):], os.path.join(tmpdir, "pkg.deb") ) )
    elif uri.startswith("http://"):
        os.system( 'wget -O "%s" "%s"' % ( os.path.join(tmpdir, "pkg.deb"), uri ) )
    elif uri.startswith("ftp://"):
        os.system( 'wget -O "%s" "%s"' % ( os.path.join(tmpdir, "pkg.deb"), uri ) )
    else:
        raise Exception ('no kinitrd package available')

    os.system( 'dpkg -x "%s" "%s"' % ( os.path.join(tmpdir, "pkg.deb"), tmpdir ) )

    if prj.has("mirror/cdrom"):
        os.system( 'cp "%s" "%s"' % ( os.path.join( tmpdir, 'opt', 'elbe', 'initrd', 'initrd-cdrom.gz' ), os.path.join(target_dir, "initrd.gz") ) )
    else:
        os.system( 'cp "%s" "%s"' % ( os.path.join( tmpdir, 'opt', 'elbe', 'initrd', 'initrd.gz' ), os.path.join(target_dir, "initrd.gz") ) )
    os.system( 'cp "%s" "%s"' % ( os.path.join( tmpdir, 'opt', 'elbe', 'initrd', 'vmlinuz' ), os.path.join(target_dir, "vmlinuz") ) )

    os.system( 'rm -r "%s"' % tmpdir )

