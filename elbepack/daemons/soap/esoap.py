#!/usr/bin/env python
#
# ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (C) 2014  Linutronix GmbH
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

import soaplib

from soaplib.service import soapmethod
from soaplib.wsgi_soap import SimpleWSGISoapApp
from soaplib.serializers.primitive import String, Array

import elbepack.db

class ESoap (SimpleWSGISoapApp):

    @soapmethod (_returns=String)
    def list_users (self):
        # use comma seperated string because array of string triggers a bug in
        # python suds :(
        ret = ""
        users = elbepack.db.list_users ()
        if not users:
            return ret
        for u in users:
            ret += u.name + ", "
        return ret

    @soapmethod (_returns=String)
    def list_projects (self):
        # use comma seperated string because array of string triggers a bug in
        # python suds :(
        ret = ""
        projects = elbepack.db.list_projects ()
        if not projects:
            return ret
        for p in projects:
            ret += p.builddir + ":" + str(p.name) + ":" + str(p.version)
            ret += str(p.status) + ":" + str(p.edited) + ", "
        return ret

    @soapmethod (String, _returns=String)
    def get_files (self, builddir):
        # use comma seperated string because array of string triggers a bug in
        # python suds :(
        ret = ""
        files = elbepack.db.get_files (builddir)
        if not files:
            return ret
        for f in files:
            ret += f + ", "
        return ret

    @soapmethod (String)
    def build (self, builddir):
        elbepack.db.build_project (builddir)

    @soapmethod (String, String, String)
    def set_xml (self, builddir, xmlfile, content):
        fn = "/tmp/" + xmlfile
        fp = file (fn, "w")
        fp.write (binascii.a2b_base64 (content))
        elbepack.db.set_xml (builddir, fn)

    @soapmethod (String)
    def del_project (self, builddir):
        elbepack.db.del_project (builddir)

    @soapmethod (String)
    def create_project (self, builddir):
        elbepack.db.create_project (builddir)
