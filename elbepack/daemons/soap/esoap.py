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

import binascii
import soaplib
import os

from soaplib.service import soapmethod
from soaplib.wsgi_soap import SimpleWSGISoapApp
from soaplib.serializers.primitive import String, Integer, Array

from tempfile import NamedTemporaryFile

from elbepack.projectmanager import ProjectManager, ProjectManagerError
from elbepack.elbexml import ValidationError
from elbepack.db import ElbeDBError, InvalidLogin

class ESoap (SimpleWSGISoapApp):

    def __init__ (self):
        SimpleWSGISoapApp.__init__ (self)
        self.pm = ProjectManager ("/var/cache/elbe")

    @soapmethod (_returns=String)
    def list_users (self):
        # use comma seperated string because array of string triggers a bug in
        # python suds :(
        ret = ""
        users = []
        try:
            users = self.pm.db.list_users ()
        except ElbeDBError as e:
            print "soap list_users failed (db error):", e
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
        projects = []
        try:
            projects = self.pm.db.list_projects ()
        except ElbeDBError as e:
            print "soap list_projects failed (db error):", e
        if not projects:
            return ret
        for p in projects:
            ret += p.builddir + "____" + str(p.name)
            ret += "____" + str(p.version) + "____" + str(p.status)
            ret += "____" + str(p.edit) + ", "
        return ret

    @soapmethod (String, _returns=String)
    def get_files (self, builddir):
        # use comma seperated string because array of string triggers a bug in
        # python suds :(
        ret = ""
        files = []
        try:
            files = self.pm.db.get_project_files (builddir)
        except ElbeDBError as e:
            print "soap get_files failed (db error):", e
        if not files:
            return ret
        for f in files:
            if f.description:
                ret += "%s (%s), " % (f.name, f.description)
            else:
                ret += f.name + ", "
        return ret

    @soapmethod (String, String, Integer, _returns=String)
    def get_file (self, builddir, filename, part):
        size = 1024 * 1024 * 5
        pos = size * part
        file_name = builddir + "/" + filename
        file_stat = os.stat (file_name)

        if (pos >= file_stat.st_size):
            return "EndOfFile"

        with file (file_name) as fp:
            if not fp:
                return "FileNotFound"
            try:
                fp.seek (pos)
                data = fp.read (size)
                return binascii.b2a_base64 (data)
            except:
                return "EndOfFile"

    @soapmethod (String)
    def build (self, builddir):
        project = ElbeProject (builddir)
        self.worker.enqueue (BuildJob (project))

    @soapmethod (String, String, String)
    def set_xml (self, builddir, xmlfile, content):
        fn = "/tmp/" + xmlfile.split('/')[-1]
        fp = file (fn, "w")
        fp.write (binascii.a2b_base64 (content))
        fp.flush ()
        try:
            self.pm.db.set_xml (builddir, fn)
        except ElbeDBError as e:
            print "soap set_xml failed (db error):", e

    @soapmethod (String)
    def del_project (self, builddir):
        try:
            self.pm.db.del_project (builddir)
        except ElbeDBError as e:
            print "soap del_project failed (db error):", e

    @soapmethod (String, String, String, String, _returns=String)
    def create_project (self, user, passwd, filename, xml):

        try:
            userid = self.pm.db.validate_login(user, passwd)
        except InvalidLogin as e:
            return str (e)

        with NamedTemporaryFile() as fp:
            fp.write (binascii.a2b_base64 (xml))
            fp.flush ()
            try:
                self.pm.create_project (userid, fp.name)
            except ProjectManagerError as e:
                return str (e)
            except ElbeDBError as e:
                return str (e)
            except OSError as e:
                return str (e)
            except ValidationError as e:
                return "Invalid XML file"

        return "OK"
