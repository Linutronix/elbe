# ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (c) 2018 Benedikt Spranger <b.spranger@linutronix.de>
#
# SPDX-License-Identifier: GPL-3.0-or-later

import os
import re
import sys

# The urlparse module is renamed to urllib.parse in Python 3.
try:
    from urllib.parse import urljoin,urlparse
except ImportError:
    from urlparse import urljoin,urlparse

from base64 import standard_b64encode
from bz2 import compress as bz2compress
from subprocess import CalledProcessError

from elbepack.treeutils import etree
from elbepack.shellhelper import system

class ArchivedirError(Exception):
    pass

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
    system(cmd)

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

def prepare_path(url):
    url = urlparse(url)
    path = url.geturl().replace("%s://"%url.scheme, '', 1)
    return re.sub(r'/$', "", path)

def get_and_append_local(url, tararchive, keep):
    if urlparse(url).netloc:
        msg = "Reject suspicious file:// URI \"{}\". ".format(url)
        msg += "Please use an absolute URI (file:///a/b/c) or a "
        msg += "relative URI (a/b/c) instead."
        raise ArchivedirError(msg)
    collect(tararchive, prepare_path(url), keep)

def get_and_append_unknown(url, _archive):
    msg = "unhandled scheme \"{}://\"".format(urlparse(url).scheme)
    raise NotImplementedError(msg)

def get_and_append_method(url):
    return {
        '': get_and_append_local,
        'file': get_and_append_local,
    }.get(urlparse(url).scheme, get_and_append_unknown)

def _combinearchivedir(xml):
    elbexml = etree(None)
    elbexml.et = xml

    archive = '.combinedarchive.tar'
    for archivedir in xml.iterfind("archivedir"):
        try:
            archiveurl = urljoin(archivedir.base, archivedir.text)
            keep = elbexml.check_boolean(archivedir, "keep-attributes")
            get_and_append = get_and_append_method(archiveurl)
            get_and_append(archiveurl, archive, keep)
            archivedir.getparent().remove(archivedir)
        except (CalledProcessError, OSError):
            msg = "Failure while processing \"" + archivedir.text + "\":\n"
            msg += str(sys.exc_info()[1])
            raise ArchivedirError(msg)

    arch = elbexml.ensure_child("archive")
    arch.set_text(enbase(archive, True))

    os.remove(archive)

    return xml

def combinearchivedir(xml):
    if xml.find("archivedir") is None:
        return xml

    return _combinearchivedir(xml)
