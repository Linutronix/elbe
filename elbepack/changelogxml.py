# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2019 Linutronix GmbH

from elbepack.treeutils import etree


class changelogs_xml:
    def __init__(self):
        self.outxml = etree(None)
        self.pkglist = self.outxml.setroot('pkgchangelogs')

    def add_pkg_changelog(self, xp, changelog_text):
        xmlpkg = self.pkglist.append('changelog')
        xmlpkg.et.attrib['name'] = xp.name
        xmlpkg.et.attrib['version'] = xp.candidate_version
        xmlpkg.et.attrib['old_version'] = xp.installed_version
        xmlpkg.et.text = changelog_text

    def write(self, fname):
        self.outxml.write(fname, encoding="utf-8")
