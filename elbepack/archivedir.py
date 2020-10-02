# ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (c) 2018 Benedikt Spranger <b.spranger@linutronix.de>
#
# SPDX-License-Identifier: GPL-3.0-or-later

import bz2
import os
import re
import sys

from urllib.parse import urljoin,urlparse

from base64 import encodebytes, standard_b64decode
from subprocess import CalledProcessError
from tempfile import NamedTemporaryFile

from elbepack.treeutils import etree
from elbepack.shellhelper import system
from elbepack.filesystem import TmpdirFilesystem


class ArchivedirError(Exception):
    pass

def enbase(fname, compress=True):
    with open(fname, "rb") as infile:
        s = infile.read()
        if compress:
            s = bz2.compress(s)
        return encodebytes(s)

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


def archive_tmpfile(arch_elem):
    fp = NamedTemporaryFile()
    fp.write(standard_b64decode(arch_elem))
    fp.file.flush()
    return fp


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

def _combinearchivedir(xml, xpath, use_volume):
    elbexml = etree(None)
    elbexml.et = xml

    tmp = TmpdirFilesystem()
    for archivedir in elbexml.all(xpath):

        try:
            archiveurl = urljoin(archivedir.et.base, archivedir.et.text)
            keep = archivedir.bool_attr("keep-attributes")
            parent = archivedir.get_parent()

            if use_volume:
                volume_attr = archivedir.et.get('volume', default='all')
                fname_suffix = volume_attr

                arch = parent.node("archive[@volume='%s']" % volume_attr)

                if arch is None:
                    arch = parent.append("archive")
                    arch.et.set("volume", volume_attr)

            else:
                arch = parent.ensure_child("archive")
                fname_suffix = ''


            get_and_append = get_and_append_method(archiveurl)

            archname = tmp.fname('archive%s.tar.bz2' % fname_suffix)
            get_and_append(archiveurl, archname, keep)
            arch.set_text(enbase(archname, True))

            parent.remove_child(archivedir)
        except (CalledProcessError, OSError):
            msg = "Failure while processing \"" + archivedir.text + "\":\n"
            msg += str(sys.exc_info()[1])
            raise ArchivedirError(msg)


def combinearchivedir(xml):
    if xml.find("//archivedir") is None:
        return xml

    _combinearchivedir(xml, "archivedir", False)
    _combinearchivedir(xml, "src-cdrom/archivedir", True)

    return xml
