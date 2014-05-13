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
    virtapt_imported = True
except ImportError:
    print "WARNING - python-apt not available: if there are multiple versions of"
    print " kinitrd packages on the mirror(s) elbe selects the first package it"
    print " has found. There is no guarantee that the latest package is used."
    print " To ensure this, the python-apt package needs to be installed."
    import urllib2
    virtapt_imported = False


class NoKinitrdException(Exception):
    pass

def get_sources_list( prj, defs ):

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

def get_initrd_pkg( prj, defs ):
    initrdname = prj.text("buildimage/kinitrd", default=defs, key="kinitrd")

    return initrdname

def get_url ( arch, suite, target_pkg, mirror ):
    try:
        packages = urllib2.urlopen("%s/dists/%s/main/binary-%s/Packages" %
          (mirror.replace("LOCALMACHINE", "localhost"), suite, arch))

        packages = packages.readlines()
        packages = filter( lambda x: x.startswith( "Filename" ), packages )
        packages = filter( lambda x: x.find( target_pkg ) != -1, packages )

        tmp = packages.pop()
        urla = tmp.split()
        url = "%s/%s" % (mirror.replace("LOCALMACHINE", "localhost"), urla[1])
    except IOError:
        url = ""
    except IndexError:
        url = ""


    return url

def get_initrd_uri( prj, defs, arch ):
    if arch == "default":
        arch  = prj.text("buildimage/arch", default=defs, key="arch")
    suite = prj.text("suite")

    name  = prj.text("name", default=defs, key="name")
    apt_sources = get_sources_list(prj, defs)

    target_pkg = get_initrd_pkg(prj, defs)

    if virtapt_imported:
        v = virtapt.VirtApt( name, arch, suite, apt_sources, "" )
        d = virtapt.apt_pkg.DepCache(v.cache)

        pkg = v.cache[target_pkg]

        c=d.get_candidate_ver(pkg)
        x=v.source.find_index(c.file_list[0][0])

        r=virtapt.apt_pkg.PackageRecords(v.cache)
        r.lookup(c.file_list[0])
        uri = x.archive_uri(r.filename)
        return uri
    else:
        url = "%s://%s/%s" % (prj.text("mirror/primary_proto"),
          prj.text("mirror/primary_host"),
          prj.text("mirror/primary_path") )
        pkg = get_url ( arch, suite, target_pkg, url )

        if pkg:
            return pkg

        for n in prj.node("mirror/url-list"):
            url = n.text("binary")
            urla = url.split()
            pkg = get_url ( arch, suite, target_pkg,
              urla[0].replace("BUILDHOST", "localhost") )

            if pkg:
                return pkg

    return ""



def copy_kinitrd( prj, target_dir, defs, arch="default" ):
    try:
        uri = get_initrd_uri(prj, defs, arch)
    except KeyError:
        raise NoKinitrdException ('no kinitrd/elbe-bootstrap package available')
        return
    except SystemError:
        raise NoKinitrdException ('a configured mirror is not reachable')
        return

    tmpdir = mkdtemp()

    if uri.startswith("file://"):
        os.system( 'cp "%s" "%s"' % ( uri[len("file://"):], os.path.join(tmpdir, "pkg.deb") ) )
    elif uri.startswith("http://"):
        os.system( 'wget -O "%s" "%s"' % ( os.path.join(tmpdir, "pkg.deb"), uri ) )
    elif uri.startswith("ftp://"):
        os.system( 'wget -O "%s" "%s"' % ( os.path.join(tmpdir, "pkg.deb"), uri ) )
    else:
        raise NoKinitrdException ('no kinitrd/elbe-bootstrap package available')

    os.system( 'dpkg -x "%s" "%s"' % ( os.path.join(tmpdir, "pkg.deb"), tmpdir ) )

    if prj.has("mirror/cdrom"):
        os.system( 'cp "%s" "%s"' % ( os.path.join( tmpdir, 'var', 'lib', 'elbe', 'initrd', 'initrd-cdrom.gz' ), os.path.join(target_dir, "initrd.gz") ) )
    else:
        os.system( 'cp "%s" "%s"' % ( os.path.join( tmpdir, 'var', 'lib', 'elbe', 'initrd', 'initrd.gz' ), os.path.join(target_dir, "initrd.gz") ) )
    os.system( 'cp "%s" "%s"' % ( os.path.join( tmpdir, 'var', 'lib', 'elbe', 'initrd', 'vmlinuz' ), os.path.join(target_dir, "vmlinuz") ) )

    os.system( 'rm -r "%s"' % tmpdir )
