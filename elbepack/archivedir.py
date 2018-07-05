# ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (c) 2018 Benedikt Spranger <b.spranger@linutronix.de>
#
# SPDX-License-Identifier: GPL-3.0-or-later

import os

from base64 import standard_b64encode
from bz2 import compress as bz2compress
from subprocess import check_call

from elbepack.treeutils import etree

def enbase(fname, compress=True):
    infile = file(fname, "r")
    s = infile.read()
    if compress:
        s = bz2compress(s)

    enc = standard_b64encode(s)
    splited = ""
    i = 0
    l_enc = len(enc)
    while i < l_enc:
        splited += (enc[i:i + 60] + "\n")
        i += 60

    return splited

def collect(tararchive, path, keep):
    if keep:
        cmd = 'tar rf ' + tararchive + ' -C '
    else:
        cmd = 'tar rf ' + tararchive + ' --owner=root --group=root -C '
    cmd += path + ' .'
    check_call(cmd, shell=True)

def chg_archive(xml, path, keep):
    if os.path.isdir(path):
        archive = '.archive.tar'
        if os.path.exists(archive):
            os.remove(archive)

        collect(archive, path, keep)
        compress = True
    else:
        archive = path
        compress = False

    arch = xml.ensure_child("archive")
    arch.set_text(enbase(archive, compress))

    if os.path.isdir(path):
        os.remove(archive)

    return xml
