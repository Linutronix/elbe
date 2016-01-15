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
from debian.copyright import Copyright, NotMachineReadableError, LicenseParagraph

import os
import sys
import io

import warnings

warnings.simplefilter('error')

def do_heuristics (fp):
    c = Copyright()
    num_licenses = 0
    for l in fp.readlines():
        if l.startswith ("License:"):
            num_licenses += 1
            _, v = l.split (":",1)
            data = {"License": v.strip()}
            lic_para = LicenseParagraph(data)
            c.add_license_paragraph (lic_para)

    if num_licenses > 0:
        return c
    else:
        return None


def get_license_list (c):
    licenses = []
    for cc in c.all_license_paragraphs():
        licenses.append (cc.license.synopsis)

    return set(licenses)


class copyright_xml (object):
    def __init__ (self):
        self.outxml = etree (None)
        self.pkglist = self.outxml.setroot('pkglicenses')

    def add_copyright_file (self, pkg_name, copyright):
        xmlpkg = self.pkglist.append('pkglicense')
        xmlpkg.et.attrib['name'] = pkg_name
        txtnode = xmlpkg.append ('text')
        txtnode.et.text = copyright

        bytesio = io.StringIO (txtnode.et.text)
        try:
            c = Copyright (bytesio)
            lics = get_license_list (c)

            xmlpkg.append('machinereadable')
            xmllic = xmlpkg.append('debian_licenses')
            for i in lics:
                l = xmllic.append('license')
                l.et.text = i

            return

        except Exception as e:
            pass

        bytesio.seek(0)
        #textio = io.TextIOWrapper (bytesio, encoding='iso-8859-1')

        c = do_heuristics (bytesio)

        if not c is None:
            lics = get_license_list (c)
            xmlpkg.append('heuristics')
            xmllic = xmlpkg.append('debian_licenses')
            for i in lics:
                l = xmllic.append('license')
                l.et.text = i

            return

        # Heuristics did not find anything either
        # just return
        return

    def write(self, fname):
        self.outxml.write (fname, encoding="iso-8859-1")

        




