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

def mappkg(pkg):
    iv = pkg.installed and pkg.installed.version
    cv = pkg.candidate and pkg.candidate.version
    return (pkg.name, iv, cv, pkgstate(pkg))

def mappkgname(c, pkgname):
    return mappkg( c[pkgname] )

def mappkg_hr(pkg):
    iv = pkg.installed and pkg.installed.version
    cv = pkg.candidate and pkg.candidate.version
    return (pkg.name, iv, cv, statestring[pkgstate(pkg)])

def mappkgname_hr(c, pkgname):
    return mappkg_hr( c[pkgname] )
