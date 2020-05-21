# ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (c) 2016 Torben Hohn <torben.hohn@linutronix.de>
# Copyright (c) 2017 Manuel Traut <manut@linutronix.de>
#
# SPDX-License-Identifier: GPL-3.0-or-later


import io
import re

import warnings
import logging

from debian.copyright import Copyright, LicenseParagraph, NotMachineReadableError, MachineReadableFormatError
from elbepack.treeutils import etree

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

    return None


def get_heuristics_license_list(c):
    licenses = []
    for cc in c.all_license_paragraphs():
        licenses.append(cc.license.synopsis)

    return set(licenses)

# TODO:py3 Remove object inheritance
# pylint: disable=useless-object-inheritance
class copyright_xml (object):
    def __init__(self):
        self.outxml = etree(None)
        self.pkglist = self.outxml.setroot('pkglicenses')

    def add_copyright_file(self, pkg_name, copyright_text):

        # pylint: disable=too-many-locals

        # remove illegal characters from copyright_text
        copyright_text, _ = remove_re.subn('', copyright_text)

        xmlpkg = self.pkglist.append('pkglicense')
        xmlpkg.et.attrib['name'] = pkg_name
        txtnode = xmlpkg.append('text')
        txtnode.et.text = copyright_text
        # in Python2 'txtnode.et.text' is a binary string whereas in Python3 it
        # is a unicode string. So make sure that 'txtnode.et.text' ends up as a
        # unicode string in both Python2 and Python3.
        bytesio = io.StringIO(txtnode.et.text.encode(encoding='utf-8',
                                                     errors='replace')
                                             .decode(encoding='utf-8',
                                                     errors='replace'))
        try:
            c = Copyright(bytesio, strict=True)
        except (NotMachineReadableError, MachineReadableFormatError) as E:
            logging.warning("Error in copyright of package '%s': %s", pkg_name, E)
        except Warning as W:
            logging.warning("Warning in copyrigh of package '%s' : %s", pkg_name, W)
        else:

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
