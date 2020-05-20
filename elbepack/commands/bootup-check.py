# ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (c) 2014, 2017 Manuel Traut <manut@linutronix.de>
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import print_function

import apt
import apt_pkg

from elbepack.treeutils import etree


def is_in_fpl(p, fpl):
    for ip in fpl:
        if ip.et.text == p.name:
            return True
    return False


def is_installed(ip, cache):
    try:
        p = cache[ip.et.text]
    except KeyError:
        print("%s is not in local apt" % ip.et.text)
        return False
    if p.current_state == apt_pkg.CURSTATE_INSTALLED:
        return True
    return False


def bootup_check(xml):

    fpl = xml.node("fullpkgs")

    apt_pkg.init()
    cache = apt_pkg.Cache()
    hl_cache = apt.cache.Cache()

    for p in hl_cache:
        if p.is_installed:
            if not is_in_fpl(p, fpl):
                print("%s installed by user" % p.name)

    for ip in fpl:
        if not is_installed(ip, cache):
            print("%s removed by user" % ip.et.text)


def bootup_info():
    with open("/etc/elbe_version", 'r') as ev:
        print(ev.read())


def run_command(_argv):
    try:
        xml = etree("/etc/elbe_base.xml")
    except IOError:
        print("/etc/elbe_base.xml removed by user")
        return -1

    bootup_check(xml)
    try:
        bootup_info()
    except IOError:
        print("/etc/elbe_version removed by user")
        return -1

    return 0
