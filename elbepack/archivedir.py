# ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (c) 2018 Benedikt Spranger <b.spranger@linutronix.de>
#
# SPDX-License-Identifier: GPL-3.0-or-later

import os

from base64 import standard_b64encode
from elbepack.treeutils import etree

def enbase(fname):
    infile = file(fname, "r")
    s = infile.read()
    enc = standard_b64encode(s)

    splited = ""
    i = 0
    l_enc = len(enc)
    while i < l_enc:
        splited += (enc[i:i + 60] + "\n")
        i += 60

    return splited

def chg_archive(xml, path, keep):
    if os.path.isdir(path):
        archive = '.archive.tbz'
        if keep:
            cmd = 'tar cfj .archive.tbz -C '
        else:
            cmd = 'tar cjf .archive.tbz --owner=root --group=root -C '
        cmd += path + ' .'
        os.system(cmd)
    else:
        archive = path
        arch = xml.ensure_child("archive")
        arch.set_text(enbase(archive))

    if os.path.isdir(path):
        os.remove(archive)

    return xml
