# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2018 Linutronix GmbH

import bz2
import os
import re
import subprocess
import sys
from base64 import encodebytes, standard_b64decode
from subprocess import CalledProcessError
from tempfile import NamedTemporaryFile
from urllib.parse import urljoin, urlparse

from elbepack.filesystem import TmpdirFilesystem
from elbepack.treeutils import etree


class ArchivedirError(Exception):
    pass


def enbase(fname, compress=True):
    with open(fname, 'rb') as infile:
        s = infile.read()
        if compress:
            s = bz2.compress(s)
        return encodebytes(s)


def collect(tararchive, path, keep):
    subprocess.run([
        'tar', 'rf', tararchive,
        *([] if keep else ['--owner=root',  '--group=root']),
        '-C', path, '.',
    ], check=True)


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

    arch = xml.ensure_child('archive')
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
    path = url.geturl().replace(f'{url.scheme}://', '', 1)
    return re.sub(r'/$', '', path)


def _get_and_append(url, archive, keep):
    urlparts = urlparse(url)

    if urlparts.scheme not in {'', 'file'}:
        raise NotImplementedError(f'unhandled scheme \"{urlparse(url).scheme}://\"')

    if urlparts.netloc:
        raise ArchivedirError(
            f'Reject suspicious file:// URI \"{url}\". '
            'Please use an absolute URI (file:///a/b/c) or a '
            'relative URI (a/b/c) instead.'
        )

    collect(archive, prepare_path(url), keep)


def _combinearchivedir(xml, xpath, use_volume):
    elbexml = etree(None)
    elbexml.et = xml

    tmp = TmpdirFilesystem()
    for archivedir in elbexml.all(xpath):

        try:
            archiveurl = urljoin(archivedir.et.base, archivedir.et.text)
            keep = archivedir.bool_attr('keep-attributes')
            parent = archivedir.get_parent()

            if use_volume:
                volume_attr = archivedir.et.get('volume', default='all')
                fname_suffix = volume_attr

                arch = parent.node(f"archive[@volume='{volume_attr}']")

                if arch is None:
                    arch = parent.append('archive')
                    arch.et.set('volume', volume_attr)

            else:
                arch = parent.ensure_child('archive')
                fname_suffix = ''

            archname = tmp.fname(f'archive{fname_suffix}.tar.bz2')
            _get_and_append(archiveurl, archname, keep)
            arch.set_text(enbase(archname, True))

            parent.remove_child(archivedir)
        except (CalledProcessError, OSError):
            msg = 'Failure while processing \"' + archivedir.tostring() + '\":\n'
            msg += str(sys.exc_info()[1])
            raise ArchivedirError(msg)


def combinearchivedir(xml):
    if xml.find('.//archivedir') is None:
        return xml

    _combinearchivedir(xml, 'archivedir', False)
    _combinearchivedir(xml, 'src-cdrom/archivedir', True)
    _combinearchivedir(xml, 'target/pbuilder/archivedir', False)

    return xml
