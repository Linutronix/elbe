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

from __future__ import print_function

# different module names in python 2 and 3
try:
    import urllib.request
    urlopen = urllib.request.urlopen
except ImportError:
    import urllib2
    urlopen = urllib2.urlopen

import os
import hashlib

from tempfile import mkdtemp

from elbepack.shellhelper import CommandError, system

try:
    from elbepack import virtapt
    from apt_pkg import TagFile
    virtapt_imported = True
except ImportError:
    print("WARNING - python-apt not available: if there are multiple versions of")
    print(" elbe-bootstrap packages on the mirror(s) elbe selects the first package it")
    print(" has found. There is no guarantee that the latest package is used.")
    print(" To ensure this, the python-apt package needs to be installed.")
    virtapt_imported = False


class NoKinitrdException(Exception):
    pass


def get_sources_list(prj, defs):

    suite = prj.text("suite")

    slist = ""
    if prj.has("mirror/primary_host"):
        mirror = "%s://%s/%s" % (prj.text("mirror/primary_proto"),
                                 prj.text("mirror/primary_host").replace(
            "LOCALMACHINE", "localhost"),
            prj.text("mirror/primary_path"))
        slist += "deb %s %s main\n" % (mirror, suite)
        slist += "deb-src %s %s main\n" % (mirror, suite)

    if prj.has("mirror/cdrom"):
        tmpdir = mkdtemp()
        kinitrd = prj.text("buildimage/kinitrd", default=defs, key="kinitrd")
        system('7z x -o%s "%s" pool/main/%s/%s dists' %
               (tmpdir, prj.text("mirror/cdrom"), kinitrd[0], kinitrd))
        slist += "deb file://%s %s main\n" % (tmpdir, suite)

    if prj.node("mirror/url-list"):
        for n in prj.node("mirror/url-list"):
            if n.has("binary"):
                tmp = n.text("binary").replace("LOCALMACHINE", "localhost")
                slist += "deb %s\n" % tmp.strip()
            if n.has("source"):
                tmp = n.text("source").replace("LOCALMACHINE", "localhost")
                slist += "deb-src %s\n" % tmp.strip()

    return slist


def get_key_list(prj):
    retval = []
    if prj.node("mirror/url-list"):
        for n in prj.node("mirror/url-list"):
            if n.has("key"):
                tmp = n.text("key").replace("LOCALMACHINE", "localhost")
                retval.append(tmp.strip())

    return retval


def get_initrd_pkg(prj, defs):
    initrdname = prj.text("buildimage/kinitrd", default=defs, key="kinitrd")

    return initrdname


def get_url(arch, suite, target_pkg, mirror, comp='main'):
    try:
        pack_url = "%s/dists/%s/%s/binary-%s/Packages" % (
            mirror.replace("LOCALMACHINE", "localhost"), suite, comp, arch)
        packages = urllib2.urlopen(pack_url, None, 10)

        packages = packages.readlines()
        packages = [x for x in packages if x.startswith("Filename")]
        packages = [x for x in packages if x.find(target_pkg) != -1]

        tmp = packages.pop()
        urla = tmp.split()
        url = "%s/%s" % (mirror.replace("LOCALMACHINE", "localhost"), urla[1])
    except IOError:
        url = ""
    except IndexError:
        url = ""

    return url


def get_initrd_uri_nonvirtapt(apt_sources, target_pkg, arch):
    for apts in apt_sources.splitlines():
        apts_split = apts.strip().split(' ')
        if apts_split[0] != 'deb':
            continue

        for comp in apts_split[2:]:
            pkg = get_url(arch, apts_split[2], target_pkg, apts_split[1], comp)

            if pkg:
                return "", pkg


def get_initrd_uri(prj, defs, arch):
    if arch == "default":
        arch = prj.text("buildimage/arch", default=defs, key="arch")
    suite = prj.text("suite")

    name = prj.text("name", default=defs, key="name")
    apt_sources = get_sources_list(prj, defs)
    apt_keys = get_key_list(prj)
    target_pkg = get_initrd_pkg(prj, defs)

    if virtapt_imported:
        try:
            v = virtapt.VirtApt(name, arch, suite, apt_sources, "", apt_keys)
        except Exception as e:
            return get_initrd_uri_nonvirtapt(apt_sources, target_pkg, arch)

        d = virtapt.apt_pkg.DepCache(v.cache)
        pkg = v.cache[target_pkg]

        c = d.get_candidate_ver(pkg)
        x = v.source.find_index(c.file_list[0][0])

        r = virtapt.apt_pkg.PackageRecords(v.cache)
        r.lookup(c.file_list[0])
        uri = x.archive_uri(r.filename)

        if not x.is_trusted:
            return "", uri

        return r.sha1_hash, uri
    else:
        return get_initrd_uri_nonvirtapt(apt_sources, target_pkg, arch)

    return "", ""


def get_dsc_size(fname):
    if not virtapt_imported:
        return 0

    tf = TagFile(fname)

    sz = os.path.getsize(fname)
    for sect in tf:
        if 'Files' in sect:
            files = sect['Files'].split('\n')
            files = [f.strip().split(' ') for f in files]
            for f in files:
                sz += int(f[1])

    return sz


def copy_kinitrd(prj, target_dir, defs, arch="default"):
    try:
        sha1, uri = get_initrd_uri(prj, defs, arch)
    except KeyError:
        raise NoKinitrdException('no elbe-bootstrap package available')
        return
    except SystemError:
        raise NoKinitrdException('a configured mirror is not reachable')
        return
    except CommandError as e:
        raise NoKinitrdException("couldn't download elbe-bootstrap package")
        return

    try:
        tmpdir = mkdtemp()

        try:
            if uri.startswith("file://"):
                system('cp "%s" "%s"' %
                       (uri[len("file://"):], os.path.join(tmpdir, "pkg.deb")))
            elif uri.startswith("http://"):
                system('wget -O "%s" "%s"' %
                       (os.path.join(tmpdir, "pkg.deb"), uri))
            elif uri.startswith("ftp://"):
                system('wget -O "%s" "%s"' %
                       (os.path.join(tmpdir, "pkg.deb"), uri))
            else:
                raise NoKinitrdException('no elbe-bootstrap package available')
        except CommandError as e:
            raise NoKinitrdException(
                "couldn't download elbe-bootstrap package")
            return

        if len(sha1) > 0:
            m = hashlib.sha1()
            with open(os.path.join(tmpdir, "pkg.deb"), "rb") as f:
                buf = f.read(65536)
                while len(buf) > 0:
                    m.update(buf)
                    buf = f.read(65536)

            if m.hexdigest() != sha1:
                raise NoKinitrdException('elbe-bootstrap failed to verify !!!')
        else:
            print("-----------------------------------------------------")
            print("WARNING:")
            print("Using untrusted elbe-bootstrap")
            print("-----------------------------------------------------")

        try:
            system('dpkg -x "%s" "%s"' %
                   (os.path.join(tmpdir, "pkg.deb"), tmpdir))
        except CommandError:
            try:
                # dpkg did not work, try falling back to ar and tar
                system('ar p "%s" data.tar.gz | tar xz -C "%s"' %
                       (os.path.join(tmpdir, "pkg.deb"), tmpdir))
            except CommandError:
                system('ar p "%s" data.tar.xz | tar xJ -C "%s"' %
                       (os.path.join(tmpdir, "pkg.deb"), tmpdir))

        # copy is done twice, because paths in elbe-bootstarp_1.0 and 0.9
        # differ
        if prj.has("mirror/cdrom"):
            system(
                'cp "%s" "%s"' %
                (os.path.join(
                    tmpdir,
                    'var',
                    'lib',
                    'elbe',
                    'initrd',
                    'initrd-cdrom.gz'),
                    os.path.join(
                    target_dir,
                    "initrd.gz")))
        else:
            system(
                'cp "%s" "%s"' %
                (os.path.join(
                    tmpdir,
                    'var',
                    'lib',
                    'elbe',
                    'initrd',
                    'initrd.gz'),
                    os.path.join(
                    target_dir,
                    "initrd.gz")))

        system(
            'cp "%s" "%s"' %
            (os.path.join(
                tmpdir,
                'var',
                'lib',
                'elbe',
                'initrd',
                'vmlinuz'),
                os.path.join(
                target_dir,
                "vmlinuz")))
    finally:
        system('rm -rf "%s"' % tmpdir)
