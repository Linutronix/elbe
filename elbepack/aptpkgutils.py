# ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (c) 2014 Torben Hohn <torbenh@linutronix.de>
# Copyright (c) 2014 Stefan Gast <stefan.gast@linutronix.de>
# Copyright (c) 2017 Manuel Traut <manut@linutronix.de>
#
# SPDX-License-Identifier: GPL-3.0-or-later

import os
import logging

import apt_pkg
import apt
from apt.package import FetchError

MARKED_INSTALL = 0
MARKED_UPGRADE = 1
MARKED_DELETE = 2
UPGRADABLE = 3
INSTALLED = 4
NOTINSTALLED = 5

statestring = {
    MARKED_INSTALL: "MARKED_INSTALL",
    MARKED_UPGRADE: "MARKED_UPGRADE",
    MARKED_DELETE: "MARKED_DELETE",
    UPGRADABLE: "UPGRADABLE",
    INSTALLED: "INSTALLED",
    NOTINSTALLED: "NOT INSTALLED"
}

def apt_pkg_md5(pkg):
    hashes = pkg._records.hashes
    for i in range(len(hashes)):
        h = str(hashes[i])
        if h.startswith("MD5"):
            return h.split(':')[1]
    return ""

def getdeps(pkg):
    for dd in pkg.dependencies:
        for d in dd:
            yield d.name


def getalldeps(c, pkgname):
    retval = []
    togo = [pkgname]

    while togo:
        pp = togo.pop()
        pkg = c[pp]

        for p in getdeps(pkg.candidate):
            if p in retval:
                continue
            if p not in c:
                continue
            retval.append(p)
            togo.append(p)

    return retval


def pkgstate(pkg):
    if pkg.marked_install:
        return MARKED_INSTALL
    elif pkg.marked_upgrade:
        return MARKED_UPGRADE
    elif pkg.marked_delete:
        return MARKED_DELETE
    elif pkg.is_upgradable:
        return UPGRADABLE
    elif pkg.is_installed:
        return INSTALLED

    return NOTINSTALLED


def pkgorigin(pkg):
    if pkg.installed:
        o = pkg.installed.origins[0]
        origin = "%s %s %s" % (o.site, o.archive, o.component)
    else:
        origin = None

    return origin

def _file_is_same(path, size, sha256):
    # type: (str, int, str) -> bool
    """Return ``True`` if the file is the same."""
    if os.path.exists(path) and os.path.getsize(path) == size:
        with open(path) as fobj:
            return apt_pkg.sha256sum(fobj) == sha256
    return False

def fetch_binary(version, destdir='', progress=None):
    # type: (str, AcquireProgress) -> str
    """Fetch the binary version of the package.

    The parameter *destdir* specifies the directory where the package will
    be fetched to.

    The parameter *progress* may refer to an apt_pkg.AcquireProgress()
    object. If not specified or None, apt.progress.text.AcquireProgress()
    is used.

    taken from python-apt-1.8.4
    (/usr/lib/python2.7/dist-packages/apt/package.py).

    ---------------------------------------------------------
    Copyright (c) 2005-2009 Canonical

    Author: Michael Vogt <michael.vogt@ubuntu.com>
    ---------------------------------------------------------

    Then fixed up to use sha256 and pass pycodestyle.
    """
    base = os.path.basename(version._records.filename)
    destfile = os.path.join(destdir, base)
    if _file_is_same(destfile, version.size, version._records.sha256_hash):
        logging.debug('Ignoring already existing file: %s', destfile)
        return os.path.abspath(destfile)
    acq = apt_pkg.Acquire(progress or apt.progress.text.AcquireProgress())
    acqfile = apt_pkg.AcquireFile(acq,
                                  version.uri,
                                  "SHA256:" + version._records.sha256_hash,
                                  version.size,
                                  base,
                                  destfile=destfile)
    acq.run()

    if acqfile.status != acqfile.STAT_DONE:
        raise FetchError("The item %r could not be fetched: %s",
                         acqfile.destfile,
                         acqfile.error_text)

    return os.path.abspath(destfile)


class PackageBase(object):

    # pylint: disable=too-many-instance-attributes

    def __init__(self, name, installed_version,
                 candidate_version, installed_md5, candidate_md5,
                 state, is_auto_installed, origin, architecture):

        # pylint: disable=too-many-arguments

        self.name = name
        self.installed_version = installed_version
        self.candidate_version = candidate_version
        self.installed_md5 = installed_md5
        self.candidate_md5 = candidate_md5
        self.state = state
        self.is_auto_installed = is_auto_installed
        self.origin = origin
        self.architecture = architecture

    def __repr__(self):
        return "<APTPackage %s-%s state: %s>" % (
            self.name, self.installed_version, statestring[self.state])

    def __eq__(self, other):
        vereq = (self.installed_version == other.installed_version)
        nameq = (self.name == other.name)

        return vereq and nameq


class APTPackage(PackageBase):
    def __init__(self, pkg, cache=None):
        if isinstance(pkg, str):
            pkg = cache[pkg]

        iver = pkg.installed and pkg.installed.version
        cver = pkg.candidate and pkg.candidate.version
        imd5 = pkg.installed and apt_pkg_md5(pkg.installed)
        cmd5 = pkg.candidate and apt_pkg_md5(pkg.candidate)

        self.state = pkgstate(pkg)
        self.is_auto_installed = pkg.is_auto_installed
        origin = pkgorigin(pkg)

        if pkg.installed:
            arch = pkg.installed.architecture
            self.installed_deb = pkg.name + '_' + iver.replace(':', '%3a') + \
                '_' + arch + '.deb'
        elif pkg.candidate:
            arch = pkg.candidate.architecture
            self.installed_deb = None
        else:
            arch = None
            self.installed_deb = None

        PackageBase.__init__(self, pkg.name, iver,
                             cver, imd5, cmd5,
                             pkgstate(pkg), pkg.is_auto_installed,
                             origin, arch)


class XMLPackage(PackageBase):
    def __init__(self, node, arch):
        PackageBase.__init__(self, node.et.text, node.et.get('version'),
                             None, node.et.get('md5'), None,
                             INSTALLED, node.et.get('auto') == 'true',
                             None, arch)
