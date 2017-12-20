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
#


from elbepack.treeutils import etree
from debian.copyright import Copyright, LicenseParagraph

import io
import re

import warnings

warnings.simplefilter('error')

remove_re = re.compile(u'[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]')


def do_heuristics(fp):
    c = Copyright()
    num_licenses = 0
    for l in fp.readlines():
        if l.startswith("License:"):
            num_licenses += 1
            _, v = l.split(":", 1)
            data = {"License": v.strip()}
            lic_para = LicenseParagraph(data)
            c.add_license_paragraph(lic_para)

    if num_licenses > 0:
        return c
    else:
        return None


def get_heuristics_license_list(c):
    licenses = []
    for cc in c.all_license_paragraphs():
        licenses.append(cc.license.synopsis)

    return set(licenses)


class copyright_xml (object):
    def __init__(self):
        self.outxml = etree(None)
        self.pkglist = self.outxml.setroot('pkglicenses')

    def add_copyright_file(self, pkg_name, copyright):

        # remove illegal characters from copyright
        copyright, _ = remove_re.subn('', copyright)

        xmlpkg = self.pkglist.append('pkglicense')
        xmlpkg.et.attrib['name'] = pkg_name
        txtnode = xmlpkg.append('text')
        txtnode.et.text = copyright

        bytesio = io.StringIO(unicode(txtnode.et.text))
        try:
            c = Copyright(bytesio)
            files = []

            for cc in c.all_files_paragraphs():
                files.append((cc.files, cc.license.synopsis, cc.copyright))

            xmlpkg.append('machinereadable')
            xmllic = xmlpkg.append('debian_licenses')
            seen = []
            for f in files:
                if f[1] in seen:
                    continue
                seen.append(f[1])
                ll = xmllic.append('license')
                ll.et.text = f[1]

            detailed = xmlpkg.append('detailed')
            for f in files:
                ff = detailed.append('files')
                for g in f[0]:
                    gg = ff.append('glob')
                    gg.et.text = g

                ll = ff.append('license')
                ll.et.text = f[1]

                cc = ff.append('copyright')
                cc.et.text = f[2]

            return

        except Exception as e:
            pass

        bytesio.seek(0)

        c = do_heuristics(bytesio)

        if c is not None:
            lics = get_heuristics_license_list(c)
            xmlpkg.append('heuristics')
            xmllic = xmlpkg.append('debian_licenses')
            for i in lics:
                ltag = xmllic.append('license')
                ltag.et.text = i

            return

        # Heuristics did not find anything either
        # just return
        return

    def write(self, fname):
        self.outxml.write(fname, encoding="iso-8859-1")
