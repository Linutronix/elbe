# ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (c) 2013-2015, 2017-2018 Manuel Traut <manut@linutronix.de>
# Copyright (c) 2014-2016 Torben Hohn <torben.hohn@linutronix.de>
# Copyright (c) 2016 John Ogness <john.ogness@linutronix.de>
#
# SPDX-License-Identifier: GPL-3.0-or-later

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

from pkg_resources import parse_version as V
from elbepack.shellhelper import CommandError, system

try:
    from apt_pkg import TagFile
    from elbepack.virtapt import get_virtaptcache
    virtapt_imported = True
except ImportError as e:
    print(e)
    print("WARNING - python-apt not available:")
    print("If there are multiple versions of elbe-bootstrap packages on the "
          "mirror(s) elbe selects the first package it has found.")
    print("There is no guarantee that the latest package is used.")
    print("To ensure this, the python-apt package needs to be installed.")
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

        # detect package with latest version number
        latest_version_str = '0+deb0u0+jessie0'
        latest_version_pos = 0
        cnt = 0
        for x in packages:
            # extract version from path/name_version_arch
            version = x.split('_')[1]
            subcount = 0
            # iterate over all parts of the version seperated by '+'
            # this is enough for elbe-bootstrap package, however '~', etc.
            # should be considered for official debian packages..
            for subv in version.split('+'):
                try:
                    if V(subv) >= V(latest_version_str.split('+')[subcount]):
                        subcount = subcount + 1
                    else:
                        break
                # current version has more parts then the reference version
                except IndexError:
                    subcount = subcount + 1
            # if iteration over all parts of the version string suceeded,
            # a new latest_version is detected
            if subcount == len(version.split('+')):
                latest_version_pos = cnt
                latest_version_str = version
            cnt = cnt + 1

        urla = packages[latest_version_pos].split()
        url = "%s/%s" % (mirror.replace("LOCALMACHINE", "localhost"), urla[1])
    except IOError:
        url = ""
    except IndexError:
        url = ""

    return url


def get_uri_nonvirtapt(apt_sources, target_pkg, arch):
    for apts in apt_sources.splitlines():
        apts_split = apts.strip().split(' ')
        if apts_split[0] != 'deb':
            continue

        for comp in apts_split[2:]:
            pkg = get_url(arch, apts_split[2], target_pkg, apts_split[1], comp)

            if pkg:
                return [(target_pkg, pkg, "")]

    return [(target_pkg, "nonexistent://" + target_pkg, "")]


def get_uri(prj, defs, arch, target_pkg, incl_deps=False):
    if arch == "default":
        arch = prj.text("buildimage/arch", default=defs, key="arch")
    suite = prj.text("suite")

    apt_sources = get_sources_list(prj, defs)
    apt_keys = get_key_list(prj)

    if virtapt_imported:
        try:
            if arch == "default":
                arch = prj.text("buildimage/arch", default=defs, key="arch")
            suite = prj.text("suite")
            v = get_virtaptcache(arch, suite, apt_sources, "", apt_keys)
        except Exception as e:
            print("python-apt failed, using fallback code")
            return get_uri_nonvirtapt(apt_sources, target_pkg, arch)

        ret = v.get_uri(suite, arch, target_pkg, incl_deps)
        return ret

    else:
        return get_uri_nonvirtapt(apt_sources, target_pkg, arch)

    return [(target_pkg, "nonexistent://" + target_pkg, "")]


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


def download_pkg(prj,
                 target_dir,
                 defs,
                 package,
                 arch="default",
                 incl_deps=False,
                 log=None):

    try:
        urilist = get_uri(prj, defs, arch, package, incl_deps)
    except KeyError:
        raise NoKinitrdException('no package %s available' % package)
    except SystemError:
        raise NoKinitrdException('a configured mirror is not reachable')
    except CommandError as e:
        raise NoKinitrdException("couldn't download package %s" % package)

    if not urilist:
        raise NoKinitrdException("couldn't download package %s" % package)

    for u in urilist:
        sha256 = u[2]
        uri = u[1]
        dest = os.path.join(target_dir, "%s.deb" % u[0])

        try:
            if uri.startswith("file://"):
                system('cp "%s" "%s"' % (uri[len("file://"):], dest))
            elif uri.startswith("http://") or uri.startswith("ftp://"):
                system('wget -O "%s" "%s"' % (dest, uri))
            else:
                raise NoKinitrdException('could not retreive %s' % uri)
        except CommandError as e:
            raise NoKinitrdException("couldn't download package %s" % package)

        if len(sha256) > 0:
            m = hashlib.sha256()
            with open(dest, "rb") as f:
                buf = f.read(65536)
                while len(buf) > 0:
                    m.update(buf)
                    buf = f.read(65536)
            if m.hexdigest() != sha256:
                raise NoKinitrdException('%s failed to verify !!!' % package)
        else:
            if log:
                log.printo("WARNING: Using untrusted %s package" % package)
            else:
                print("-----------------------------------------------------")
                print("WARNING:")
                print("Using untrusted %s package" % package)
                print("-----------------------------------------------------")

    return [y[0] for y in urilist]


def extract_pkg(prj, target_dir, defs, package, arch="default",
                incl_deps=False, log=None):

    pkgs = download_pkg(prj, target_dir, defs, package, arch, incl_deps, log)

    for package in pkgs:
        ppath = os.path.join(target_dir, "%s.deb" % package)
        try:
            system('dpkg -x "%s" "%s"' % (ppath, target_dir))
        except CommandError:
            try:
                # dpkg did not work, try falling back to ar and tar
                system('ar p "%s" data.tar.gz | tar xz -C "%s"' % (ppath,
                                                                   target_dir))
            except CommandError:
                system('ar p "%s" data.tar.xz | tar xJ -C "%s"' % (ppath,
                                                                   target_dir))
        system('rm -f "%s"' % ppath)


def copy_kinitrd(prj, target_dir, defs, arch="default"):

    target_pkg = get_initrd_pkg(prj, defs)

    try:
        tmpdir = mkdtemp()
        extract_pkg(prj, tmpdir, defs, target_pkg, arch)

        # copy is done twice, because paths in elbe-bootstarp_1.0 and 0.9
        # differ
        initrd = os.path.join(tmpdir, 'var', 'lib', 'elbe', 'initrd')
        if prj.has("mirror/cdrom"):
            system('cp "%s" "%s"' % (os.path.join(initrd, 'initrd-cdrom.gz'),
                                     os.path.join(target_dir, "initrd.gz")))
        else:
            system('cp "%s" "%s"' % (os.path.join(initrd, 'initrd.gz'),
                                     os.path.join(target_dir, "initrd.gz")))

        system('cp "%s" "%s"' % (os.path.join(initrd, 'vmlinuz'),
                                 os.path.join(target_dir, "vmlinuz")))
    finally:
        system('rm -rf "%s"' % tmpdir)
