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

import elbepack
from elbepack.treeutils import etree
from elbepack.validate import validate_xml
from elbepack.xmldefaults import ElbeDefaults
from elbepack.version import elbe_version


class ValidationError(Exception):
    def __init__(self):
        pass

    def __repr__(self):
	return "Elbe XML Validation Error"


class ElbeXML(object):
    def __init__(self, fname, buildtype=None):
        if not validate_xml(fname):
            raise ValidationError

        self.xml = etree( fname )
        self.prj = self.xml.node("/project")
        self.tgt = self.xml.node("/target")

        if buildtype:
            pass
        elif self.xml.has( "project/buildtype" ):
            buildtype = self.xml.text( "/project/buildtype" )
        else:
            buildtype = "nodefaults"
        self.defs = ElbeDefaults(buildtype)

    def text(self, txt, key=None):
        if key:
            return self.xml.text(txt, default=self.defs, key=key)
        else:
            return self.xml.text(txt)

    def get_primary_mirror (self, cdrompath):
            if self.prj.has("mirror/primary_host"):
                    m = self.prj.node("mirror")

                    mirror = m.text("primary_proto") + "://"
                    mirror +=m.text("primary_host")  + "/"
                    mirror +=m.text("primary_path")

            elif self.prj.has("mirror/cdrom") and cdrompath:
                     mirror = "file://%s/debian" % cdrompath

            return mirror.replace("LOCALMACHINE", "10.0.2.2")


    # XXX: maybe add cdrom path param ?
    def create_apt_sources_list (self):
            if not self.prj.has("mirror") and not self.prj.has("mirror/cdrom"):
                    return "# no mirrors configured"

            if self.prj.has("mirror/primary_host"):
                    mirror  = "deb " + self.get_primary_mirror (None)
                    mirror += " " + self.prj.text("suite") + " main\n"

                    for url in self.prj.node("mirror/url-list"):
                          if url.has("binary"):
                               mirror += "deb " + url.text("binary").strip() + "\n"
                          if url.has("source"):
                               mirror += "deb-src "+url.text("source").strip()+"\n"

            if self.prj.has("mirror/cdrom"):
                    mirror += "deb copy:///mnt %s main\n" % (project.text("suite"))

            return mirror.replace("LOCALMACHINE", "10.0.2.2")

