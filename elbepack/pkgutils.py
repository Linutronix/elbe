# ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (c) 2013-2015, 2017-2018 Manuel Traut <manut@linutronix.de>
# Copyright (c) 2014-2016 Torben Hohn <torben.hohn@linutronix.de>
# Copyright (c) 2016 John Ogness <john.ogness@linutronix.de>
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import print_function

import os

from apt_pkg import TagFile
from elbepack.shellhelper import CommandError, system
from elbepack.virtapt import get_virtaptcache
from elbepack.hashes import validate_sha256, HashValidationFailed


class NoPackageException(Exception):
    pass


def get_sources_list(prj):

    suite = prj.text("suite")

    slist = ""
    if prj.has("mirror/primary_host"):
        mirror = "%s://%s/%s" % (prj.text("mirror/primary_proto"),
                                 prj.text("mirror/primary_host").replace(
            "LOCALMACHINE", "localhost"),
            prj.text("mirror/primary_path"))
        slist += "deb %s %s main\n" % (mirror, suite)
        slist += "deb-src %s %s main\n" % (mirror, suite)

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


def get_uri(prj, defs, arch, target_pkg, incl_deps=False):
    if arch == "default":
        arch = prj.text("buildimage/arch", default=defs, key="arch")
    suite = prj.text("suite")

    apt_sources = get_sources_list(prj)
    apt_keys = get_key_list(prj)

    if arch == "default":
        arch = prj.text("buildimage/arch", default=defs, key="arch")
    suite = prj.text("suite")
    v = get_virtaptcache(arch, suite, apt_sources, "", apt_keys)

    ret = v.get_uri(target_pkg, incl_deps)
    return ret


def get_dsc_size(fname):
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

    # pylint: disable=too-many-arguments
    # pylint: disable=too-many-locals
    # pylint: disable=too-many-branches

    try:
        urilist = get_uri(prj, defs, arch, package, incl_deps)
    except KeyError:
        raise NoPackageException('no package %s available' % package)
    except SystemError:
        raise NoPackageException('a configured mirror is not reachable')
    except CommandError:
        raise NoPackageException("couldn't download package %s" % package)

    if not urilist:
        raise NoPackageException("couldn't download package %s" % package)

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
                raise NoPackageException('could not retreive %s' % uri)
        except CommandError:
            raise NoPackageException("couldn't download package %s" % package)

        if sha256:
            try:
                validate_sha256(dest, sha256)
            except HashValidationFailed as e:
                raise NoPackageException('%s failed to verify: %s' % package,
                                         e.message)
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

    # pylint: disable=too-many-arguments

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
