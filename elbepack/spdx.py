# ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (C) 2017  Linutronix GmbH
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

import bz2
import json
import os
import sys
import urllib
import urllib2

from elbepack.filesystem  import TmpdirFilesystem
from libarchive import file_writer

def download_spdx(tmp, baseurl, path, log):
    if path.startswith("/"):
        path = path[1:]

    tmp.mkdir_p(os.path.dirname(path))

    try:
        url = baseurl + '/' + path
        req = urllib2.Request(url)
        response = urllib2.urlopen(req)

        with open(path, 'wb') as f:
            f.write(response.read())

    except urllib2.HTTPError as e:
        log.printo("HTTP Error {}: {}".format(e.code, e.reason))
        log.printo("SPDX download {} failed.".format(url))

    except urllib2.URLError as e:
        log.printo("URL Error: {}".format(e.reason))
        log.printo("SPDX download {} failed.".format(url))

def update_cache(xml, cache, log):
    decomp = bz2.BZ2Decompressor()

    for mirror in xml.get_spdx_mirrors ():
        url = mirror + '/spdx.list.bz2'
        try:
            req = urllib2.Request(url)
            response = urllib2.urlopen(req)
            filemap = json.loads(decomp.decompress(response.read()))
            cache.append({"baseurl": mirror, "map": filemap})
        except urllib2.HTTPError as e:
            log.printo("HTTP Error {}: {}".format(e.code, e.reason))
            log.printo("SPDX List {} skipped.".format(url))
        except urllib2.URLError as e:
            log.printo("URL Error: {}".format(e.reason))
            log.printo("SPDX List {} skipped.".format(url))

def get_spdx(target, xml, log):
    cur = os.getcwd()
    tmpdir = TmpdirFilesystem()
    os.chdir(tmpdir.path)

    genfiles = []
    cache = []
    spdxarchive = os.path.join(target, 'spdx.7z')
    update_cache(xml, cache, log)

    src = os.path.join (target, 'srcrepo/pool')
    for root, dirs, files in os.walk(src):
        for f in files:
            # skip *.dsc files
            if f.endswith('.dsc'):
                continue

            pathlist = None
            for c in cache:
                filemap = c['map']
                try:
                    pathlist = filemap[f]
                except KeyError:
                    continue
                break

            if not pathlist:
                log.printo("No SPDX files for {} found.".format(f))
                continue

            for path in pathlist:
                download_spdx(tmpdir, c['baseurl'], path, log)

    with file_writer(spdxarchive, '7zip') as archive:
        archive.add_files(".")
        genfiles = [spdxarchive]

    os.chdir(cur)

    return genfiles
