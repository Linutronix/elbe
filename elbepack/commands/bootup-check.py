#!/usr/bin/env python

# ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (C) 2014  Linutronix GmbH
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

import apt
import apt_pkg

from elbepack.treeutils import etree

def is_in_fpl (p, fpl):
    for ip in fpl:
        if ip.et.text == p.name:
            return True
    return False

def is_installed (ip, cache):
    try:
        p = cache[ip.et.text]
    except KeyError:
        print("%s is not in local apt" % ip.et.text)
        return False
    if p.current_state == apt_pkg.CURSTATE_INSTALLED:
        return True
    return False

def bootup_check (xml):

    fpl = xml.node ("fullpkgs")

    apt_pkg.init ()
    cache = apt_pkg.Cache ()
    hl_cache = apt.cache.Cache ()

    for p in hl_cache:
        if p.is_installed:
            if not is_in_fpl (p, fpl):
                print("%s installed by user" % p.name)

    for ip in fpl:
         if not is_installed (ip, cache):
                print("%s removed by user" % ip.et.text)

def bootup_info ():
    with open ("/etc/elbe_version", 'r') as ev:
        print(ev.read())

def run_command (argv):
    try:
        xml = etree ("/etc/elbe_base.xml")
    except IOError:
        print("/etc/elbe_base.xml removed by user")
        return -1

    bootup_check (xml)
    try:
        bootup_info ()
    except IOError:
        print("/etc/elbe_version removed by user")
        return -1
