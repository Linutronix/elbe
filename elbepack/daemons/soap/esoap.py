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

from soaplib.service import soapmethod
from soaplib.wsgi_soap import SimpleWSGISoapApp
from soaplib.serializers.primitive import String, Array

from elbepack.db import ElbeDB, ElbeDBError
from elbepack.elbeproject import ElbeProject
from elbepack.asyncworker import AsyncWorker, BuildJob

class ESoap (SimpleWSGISoapApp):

    def __init__ (self):
        SimpleWSGISoapApp.__init__ (self)
        db = ElbeDB ()
        self.worker = AsyncWorker (db)

    @soapmethod (_returns=String)
    def list_users (self):
        # use comma seperated string because array of string triggers a bug in
        # python suds :(
        ret = ""
        users = []
        db = ElbeDB ()
        try:
            users = db.list_users ()
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
        db = ElbeDB ()
        try:
            projects = db.list_projects ()
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
        db = ElbeDB ()
        try:
            files = db.get_project_files (builddir)
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

    @soapmethod (String, String, _returns=String)
    def get_file (self, builddir, filename):
        fp = file (builddir + "/" + filename)
        if not fp:
            return "FileNotFound"
        return binascii.b2a_base64 (fp.read ())

    @soapmethod (String)
    def build (self, builddir):
        project = ElbeProject (builddir)
        self.worker.enqueue (BuildJob (project))

    @soapmethod (String, String, String)
    def set_xml (self, builddir, xmlfile, content):
        db = ElbeDB ()
        fn = "/tmp/" + xmlfile.split('/')[-1]
        fp = file (fn, "w")
        fp.write (binascii.a2b_base64 (content))
        fp.flush ()
        try:
            db.set_xml (builddir, fn)
        except ElbeDBError as e:
            print "soap set_xml failed (db error):", e

    @soapmethod (String)
    def del_project (self, builddir):
        db = ElbeDB ()
        try:
            db.del_project (builddir)
        except ElbeDBError as e:
            print "soap del_project failed (db error):", e

    @soapmethod (String)
    def create_project (self, builddir):
        db = ElbeDB ()
        try:
            db.create_project (builddir)
        except ElbeDBError as e:
            print "soap create_project failed (db error):", e
