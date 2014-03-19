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

MARKED_INSTALL = 0
MARKED_UPGRADE = 1
MARKED_DELETE = 2
UPGRADABLE = 3
INSTALLED = 4
NOTINSTALLED = 5

statestring = {
    MARKED_INSTALL : "MARKED_INSTALL",
    MARKED_UPGRADE : "MARKED_UPGRADE",
    MARKED_DELETE  : "MARKED_DELETE",
    UPGRADABLE     : "UPGRADABLE",
    INSTALLED      : "INSTALLED",
    NOTINSTALLED   : "NOT INSTALLED"
}

def getdeps(pkg):
    for dd in pkg.dependencies:
        for d in dd:
            yield d.name

def getalldeps(c, pkgname):
    retval = []
    togo = [pkgname]

    while len(togo):
        pp = togo.pop()
        pkg = c[ pp ]

        for p in getdeps(pkg.candidate):
            if p in retval:
                continue
            if not p in c:
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
    else:
        return NOTINSTALLED

class APTPackage(object):
    def __init__(self, pkg, cache=None):
        if type(pkg) == str:
            pkg = cache[pkg]

        self.name = pkg.name
        self.installed_version = pkg.installed and pkg.installed.version
        self.candidate_version = pkg.candidate and pkg.candidate.version
        self.installed_md5 = pkg.installed and pkg.installed.md5
        self.candidate_md5 = pkg.candidate and pkg.candidate.md5
        self.state = pkgstate(pkg)
        self.is_auto_installed = pkg.is_auto_installed
        if pkg.installed:
            o = pkg.installed.origins[0]
            self.origin = "%s %s %s" % (o.site, o.archive, o.component)
        else:
            self.origin = None

        if pkg.installed:
            self.architecture = pkg.installed.architecture
        elif pkg.candidate:
            self.architecture = pkg.candidate.architecture
        else:
            self.architecture = None

    def __repr__(self):
        return "<APTPackage %s-%s state: %s>" % (self.name, self.installed_version, statestring[self.state])

