# ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (c) 2019 Torben Hohn <torben.hohn@linutronix.de>
#
# SPDX-License-Identifier: GPL-3.0-or-later

import re
from elbepack.treeutils import etree


remove_re = re.compile(u'[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]')

# TODO:py3 Remove object inheritance
# pylint: disable=useless-object-inheritance
class changelogs_xml(object):
    def __init__(self):
        self.outxml = etree(None)
        self.pkglist = self.outxml.setroot('pkgchangelogs')

    def add_pkg_changelog(self, xp, changelog_text):
        changelog_text, _ = remove_re.subn('', changelog_text)

        xmlpkg = self.pkglist.append('changelog')
        xmlpkg.et.attrib['name'] = xp.name
        xmlpkg.et.attrib['version'] = xp.candidate_version
        xmlpkg.et.attrib['old_version'] = xp.installed_version

        try:
            xmlpkg.et.text = changelog_text.decode('utf-8')
        except ValueError:
            print(changelog_text)

    def write(self, fname):
        self.outxml.write(fname, encoding="utf-8")
