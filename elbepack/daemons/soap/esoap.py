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
from soaplib.wsgi_soap import SimpleWSGISoapApp, request
from soaplibfix import String, Integer, Array
from soaplib.serializers.primitive import Boolean

from cherrypy.process.plugins import SimplePlugin

from tempfile import NamedTemporaryFile

from elbepack.projectmanager import ProjectManager
from elbepack.shellhelper import system

from faults import soap_faults

from datatypes import SoapProject, SoapFile
from authentication import authenticated_admin, authenticated_uid

# Deactivate the FutureWarning from wsgi_soap:
#
# /usr/lib/pymodules/python2.7/soaplib/wsgi_soap.py:219: FutureWarning: The behavior of this method will change in future versions. Use specific 'len(elem)' or 'elem is not None' test instead.
#   if payload:
#   /usr/lib/pymodules/python2.7/soaplib/wsgi_soap.py:236: FutureWarning: The behavior of this method will change in future versions. Use specific 'len(elem)' or 'elem is not None' test instead.
#     if payload:
import warnings
warnings.simplefilter(action = "ignore", category = FutureWarning)

class ESoap (SimpleWSGISoapApp, SimplePlugin):

    def __init__ (self,engine):
        SimpleWSGISoapApp.__init__ (self)
        self.pm = ProjectManager ("/var/cache/elbe")
        SimplePlugin.__init__(self,engine)
        self.subscribe()

    def stop(self):
        self.pm.stop()

    @soapmethod (String, String, _returns=Boolean )
    @soap_faults
    def login(self, user, passwd):
        s = request.environ['beaker.session']
        s['userid'] = self.pm.db.validate_login(user, passwd)
        s.save()

        return True


    @soapmethod (_returns=Array(String))
    @authenticated_admin
    @soap_faults
    def list_users (self):
        users = self.pm.db.list_users ()
        return [u.name for u in users]

    @soapmethod (_returns=Array(SoapProject))
    @authenticated_admin
    @soap_faults
    def list_projects (self):
        projects = self.pm.db.list_projects ()
        return [SoapProject(p) for p in projects]

    @soapmethod (String, _returns=Array(SoapFile))
    @authenticated_uid
    @soap_faults
    def get_files (self, uid, builddir):
        files = self.pm.db.get_project_files (builddir)
        return [SoapFile(f) for f in files]

    @soapmethod (String, String, Integer, _returns=String)
    @authenticated_uid
    @soap_faults
    def get_file (self, uid, builddir, filename, part):
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
    @authenticated_uid
    @soap_faults
    def build_sysroot (self, uid, builddir):
        self.pm.open_project (uid, builddir)
        self.pm.build_sysroot (uid)

    @soapmethod (String, Boolean, Boolean)
    @authenticated_uid
    @soap_faults
    def build (self, uid, builddir, build_bin, build_src):
        self.pm.open_project (uid, builddir)
        self.pm.build_current_project (uid, build_bin, build_src)

    @soapmethod (String)
    @authenticated_uid
    @soap_faults
    def build_pbuilder (self, uid, builddir):
        self.pm.open_project (uid, builddir)
        self.pm.build_pbuilder (uid)

    @soapmethod (String, String)
    @authenticated_uid
    @soap_faults
    def set_xml (self, uid, builddir, xml, skip_urlcheck):
        self.pm.open_project (uid, builddir, skip_urlcheck=skip_urlcheck)

        with NamedTemporaryFile() as fp:
            fp.write (binascii.a2b_base64 (xml))
            fp.flush ()
            self.pm.set_current_project_xml (uid, fp.name)

    @soapmethod (String)
    @authenticated_uid
    @soap_faults
    def start_cdrom (self, uid, builddir):
        self.pm.open_project (uid, builddir, skip_urlcheck=True)

        cdrom_fname = os.path.join (builddir, "uploaded_cdrom.iso")

        # Now write empty File
        fp = open (cdrom_fname, "w")
        fp.close()

    @soapmethod (String, String)
    @authenticated_uid
    @soap_faults
    def append_cdrom (self, uid, builddir, data):
        self.pm.open_project (uid, builddir, skip_urlcheck=True)

        cdrom_fname = os.path.join (builddir, "uploaded_cdrom.iso")

        # Now append data to cdrom_file
        fp = open (cdrom_fname, "a")
        fp.write (binascii.a2b_base64 (data))
        fp.close()

    @soapmethod (String)
    @authenticated_uid
    @soap_faults
    def finish_cdrom (self, uid, builddir):
        self.pm.open_project (uid, builddir, skip_urlcheck=True)
        self.pm.set_current_project_upload_cdrom (uid)

    @soapmethod (String)
    @authenticated_uid
    @soap_faults
    def start_pdebuild (self, uid, builddir):
        self.pm.open_project (uid, builddir)

        pdebuild_fname = os.path.join (builddir, "current_pdebuild.tar.gz")

        # Now write empty File
        fp = open (pdebuild_fname, "w")
        fp.close()

    @soapmethod (String, String)
    @authenticated_uid
    @soap_faults
    def append_pdebuild (self, uid, builddir, data):
        self.pm.open_project (uid, builddir)

        pdebuild_fname = os.path.join (builddir, "current_pdebuild.tar.gz")

        # Now write empty File
        fp = open (pdebuild_fname, "a")
        fp.write (binascii.a2b_base64 (data))
        fp.close()

    @soapmethod (String)
    @authenticated_uid
    @soap_faults
    def finish_pdebuild (self, uid, builddir):
        self.pm.open_project (uid, builddir)
        self.pm.build_current_pdebuild (uid)

    @soapmethod (String)
    @authenticated_uid
    @soap_faults
    def reset_project (self, uid, builddir):
        self.pm.db.reset_project (builddir, True)

    @soapmethod (String)
    @authenticated_uid
    @soap_faults
    def del_project (self, uid, builddir):
        self.pm.del_project (uid, builddir)

    @soapmethod (String, Boolean, _returns=String)
    @authenticated_uid
    @soap_faults
    def create_project (self, uid, xml, skip_urlcheck):
        with NamedTemporaryFile() as fp:
            fp.write (binascii.a2b_base64 (xml))
            fp.flush ()
            prjid = self.pm.create_project (uid, fp.name, skip_urlcheck=skip_urlcheck)

        return prjid

    @soapmethod (String, _returns=Boolean)
    @authenticated_uid
    @soap_faults
    def get_project_busy (self, uid, builddir):
        self.pm.open_project (uid, builddir)

        return self.pm.current_project_is_busy (uid)

    @soapmethod ()
    @authenticated_uid
    @soap_faults
    def shutdown_initvm (self, uid):
        system ("systemctl --no-block poweroff")

