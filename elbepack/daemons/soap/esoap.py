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
import os

from cherrypy.process.plugins import SimplePlugin

from tempfile import NamedTemporaryFile

from elbepack.shellhelper import system

from faults import soap_faults

from elbepack.db import Project, User
from datatypes import SoapProject, SoapFile
from authentication import authenticated_admin, authenticated_uid

from subprocess import Popen, PIPE

from spyne.service import ServiceBase
from spyne.decorator import rpc
from spyne.model.primitive import String, Boolean, Integer
from spyne.model.complex import Array, Iterable

from threading import local

class ESoap (SimplePlugin, ServiceBase):

    __name__ = 'soap'

    def __init__ (self,engine):
        SimplePlugin.__init__(self,engine)
        self.subscribe()

    def stop(self):
        self.app.pm.stop()

    @rpc (String, String, _returns=Boolean )
    @soap_faults
    def login(self, user, passwd):
        s = self.transport.req_env['beaker.session']
        s['userid'] = self.app.pm.db.validate_login(user, passwd)
        s.save()
        return True


    @rpc (_returns=Array(String))
    @soap_faults
    @authenticated_admin
    def list_users (ctx):
        return [u.name for u in ctx.app.pm.db.list_users ()]

    @rpc (_returns=Array(SoapProject))
    @soap_faults
    @authenticated_admin
    def list_projects (ctx):
        return ctx.app.pm.db.list_projects()

    @rpc (String, String, _returns=Array(SoapFile))
    @authenticated_uid
    @soap_faults
    def get_files (self, uid, builddir, _returns=Array(SoapFile)):
        files = self.app.pm.db.get_project_files (builddir)
        return [SoapFile(f) for f in files]

    @rpc (String, String, Integer, _returns=String)
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

    @rpc (String)
    @authenticated_uid
    @soap_faults
    def build_chroot_tarball (self, uid, builddir):
        self.app.pm.open_project (uid, builddir)
        self.app.pm.build_chroot_tarball (uid)

    @rpc (String)
    @authenticated_uid
    @soap_faults
    def build_sysroot (self, uid, builddir):
        self.app.pm.open_project (uid, builddir)
        self.app.pm.build_sysroot (uid)

    @rpc (String, Boolean, Boolean)
    @authenticated_uid
    @soap_faults
    def build (self, uid, builddir, build_bin, build_src):
        self.app.pm.open_project (uid, builddir)
        self.app.pm.build_current_project (uid, build_bin, build_src)

    @rpc (String)
    @authenticated_uid
    @soap_faults
    def build_pbuilder (self, uid, builddir):
        self.app.pm.open_project (uid, builddir)
        self.app.pm.build_pbuilder (uid)

    @rpc (String, String, Boolean)
    @authenticated_uid
    @soap_faults
    def set_xml (self, uid, builddir, xml, skip_urlcheck):
        self.app.pm.open_project (uid, builddir, skip_urlcheck=skip_urlcheck)

        with NamedTemporaryFile() as fp:
            fp.write (binascii.a2b_base64 (xml))
            fp.flush ()
            self.app.pm.set_current_project_xml (uid, fp.name)

    @rpc (String)
    @authenticated_uid
    @soap_faults
    def start_cdrom (self, uid, builddir):
        self.app.pm.open_project (uid, builddir, skip_urlcheck=True)

        cdrom_fname = os.path.join (builddir, "uploaded_cdrom.iso")

        # Now write empty File
        fp = open (cdrom_fname, "w")
        fp.close()

    @rpc (String, String)
    @authenticated_uid
    @soap_faults
    def append_cdrom (self, uid, builddir, data):
        self.app.pm.open_project (uid, builddir, skip_urlcheck=True)

        cdrom_fname = os.path.join (builddir, "uploaded_cdrom.iso")

        # Now append data to cdrom_file
        fp = open (cdrom_fname, "a")
        fp.write (binascii.a2b_base64 (data))
        fp.close()

    @rpc (String)
    @authenticated_uid
    @soap_faults
    def finish_cdrom (self, uid, builddir):
        self.app.pm.open_project (uid, builddir, skip_urlcheck=True)
        self.app.pm.set_current_project_upload_cdrom (uid)

    @rpc (String)
    @authenticated_uid
    @soap_faults
    def start_pdebuild (self, uid, builddir):
        self.app.pm.open_project (uid, builddir)

        pdebuild_fname = os.path.join (builddir, "current_pdebuild.tar.gz")

        # Now write empty File
        fp = open (pdebuild_fname, "w")
        fp.close()

    @rpc (String, String)
    @authenticated_uid
    @soap_faults
    def append_pdebuild (self, uid, builddir, data):
        self.app.pm.open_project (uid, builddir)

        pdebuild_fname = os.path.join (builddir, "current_pdebuild.tar.gz")

        # Now write empty File
        fp = open (pdebuild_fname, "a")
        fp.write (binascii.a2b_base64 (data))
        fp.close()

    @rpc (String)
    @authenticated_uid
    @soap_faults
    def finish_pdebuild (self, uid, builddir):
        self.app.pm.open_project (uid, builddir)
        self.app.pm.build_current_pdebuild (uid)

    @rpc (String)
    @authenticated_uid
    @soap_faults
    def reset_project (self, uid, builddir):
        self.app.pm.db.reset_project (builddir, True)

    @rpc (String)
    @authenticated_uid
    @soap_faults
    def del_project (self, uid, builddir):
        self.app.pm.del_project (uid, builddir)

    @rpc(String, Boolean, _returns=String)
    @authenticated_uid
    @soap_faults
    def create_project (self, uid, xml, skip_urlcheck):
        with NamedTemporaryFile() as fp:
            fp.write (binascii.a2b_base64 (xml))
            fp.flush ()
            prjid = self.app.pm.create_project (uid, fp.name, skip_urlcheck=skip_urlcheck)

        return prjid

    @rpc (String, _returns=String)
    @authenticated_uid
    @soap_faults
    def get_project_busy (self, uid, builddir):
        self.app.pm.open_project (uid, builddir)
        ret,log = self.app.pm.current_project_is_busy (uid)
        if not ret:
            return 'FINISH'
        return log

    @rpc ()
    @authenticated_uid
    @soap_faults
    def shutdown_initvm (self, uid):
        system ("systemctl --no-block poweroff")

