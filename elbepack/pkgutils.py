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
            "LOCALMACHINE", "10.0.2.2"),
            prj.text("mirror/primary_path"))
        slist += "deb %s %s main\n" % (mirror, suite)
        slist += "deb-src %s %s main\n" % (mirror, suite)

    if prj.node("mirror/url-list"):
        for n in prj.node("mirror/url-list"):
            if n.has("binary"):
                tmp = n.text("binary").replace("LOCALMACHINE", "10.0.2.2")
                slist += "deb %s\n" % tmp.strip()
            if n.has("source"):
                tmp = n.text("source").replace("LOCALMACHINE", "10.0.2.2")
                slist += "deb-src %s\n" % tmp.strip()

    return slist


def get_key_list(prj):
    retval = []
    if prj.node("mirror/url-list"):
        for n in prj.node("mirror/url-list"):
            if n.has("key"):
                tmp = n.text("key").replace("LOCALMACHINE", "10.0.2.2")
                retval.append(tmp.strip())

    return retval


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
