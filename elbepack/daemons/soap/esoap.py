# ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (c) 2014-2018 Manuel Traut <manut@linutronix.de>
# Copyright (c) 2015-2016, 2018 Torben Hohn <torben.hohn@linutronix.de>
# Copyright (c) 2016 Claudius Heine <ch@denx.de>
# Copyright (c) 2017 Philipp Arras <philipp.arras@linutronix.de>
#
# SPDX-License-Identifier: GPL-3.0-or-later

import binascii
import os
import tarfile
import fnmatch
import sys

from tempfile import NamedTemporaryFile

from spyne.service import ServiceBase
from spyne.decorator import rpc
from spyne.model.primitive import String, Boolean, Integer
from spyne.model.complex import Array

from elbepack.shellhelper import system, command_out
from elbepack.version import elbe_version, is_devel
from elbepack.elbexml import ValidationMode
from elbepack.filesystem import hostfs

from .faults import soap_faults
from .datatypes import SoapProject, SoapFile, SoapCmdReply
from .authentication import authenticated_admin, authenticated_uid


class ESoap (ServiceBase):

    # pylint: disable=too-many-public-methods

    __name__ = 'soap'

    def __init__(self):
        self.app = None
        self.transport = None

    @rpc(_returns=String)
    @soap_faults
    def get_version(self):
        # pylint: disable=no-self-use
        return elbe_version

    @rpc(String, String, _returns=Boolean)
    @soap_faults
    def login(self, user, passwd):
        s = self.transport.req_env['beaker.session']
        s['userid'] = self.app.pm.db.validate_login(user, passwd)
        s.save()
        return True

    @rpc(_returns=Array(String))
    @soap_faults
    @authenticated_admin
    def list_users(self):
        return [u.name for u in self.app.pm.db.list_users()]

    @rpc(String, String(max_occurs='unbounded'), _returns=SoapCmdReply)
    @soap_faults
    @authenticated_admin
    def install_elbe_version(self, version, pkglist):
        # pylint: disable=no-self-use
        if is_devel:
            return SoapCmdReply(10,
                                'Initvm is in devel mode: installing another\n'
                                'elbe version will not have any effect.\n')

        pkgs = ['"%s=%s*"' % (p, version) for p in pkglist]

        # Prevent, that elbe daemon is restarted by the
        # prerm/postinst scripts.
        # elbe daemon does it itself, because cherrypy
        # notices that.
        hostfs.write_file("usr/sbin/policy-rc.d",
                          0o755, "#!/bin/sh\nexit 101\n")
        try:
            env = {'LANG': 'C',
                   'LANGUAGE': 'C',
                   'LC_ALL': 'C',
                   'DEBIAN_FRONTEND': 'noninteractive',
                   'DEBCONF_NONINTERACTIVE_SEEN': 'true'}

            cmd = 'apt-get install -y --force-yes %s' % ' '.join(pkgs)

            ret, out = command_out(cmd, env_add=env)
        finally:
            hostfs.remove('usr/sbin/policy-rc.d')

        return SoapCmdReply(ret, out)

    @rpc(String, String, String, String, Boolean)
    @soap_faults
    @authenticated_admin
    def add_user(self, name, fullname, password, email, admin):

        # pylint: disable=too-many-arguments

        self.app.pm.db.add_user(name, fullname, password, email, admin)

    @rpc(_returns=Array(SoapProject))
    @soap_faults
    @authenticated_admin
    def list_projects(self):
        return self.app.pm.db.list_projects()

    @rpc(String, _returns=SoapProject)
    @soap_faults
    @authenticated_uid
    def get_project(self, uid, builddir):
        self.app.pm.open_project(uid, builddir)
        return self.app.pm.db.get_project_data(builddir)

    @rpc(String, _returns=Array(SoapFile))
    @authenticated_uid
    @soap_faults
    def get_files(self, uid, builddir):
        self.app.pm.open_project(uid, builddir)
        files = self.app.pm.db.get_project_files(builddir)
        return [SoapFile(f) for f in files]

    @rpc(String, String, String, Integer, _returns=Integer)
    @authenticated_uid
    @soap_faults
    def upload_file(self, uid, builddir, fname, blob, part):

        # pylint: disable=too-many-arguments

        fn = os.path.join(builddir, fname)
        if part == 0:
            if self.app.pm.db.is_busy(builddir):
                return -1
            self.app.pm.db.set_busy(builddir, ["empty_project", "needs_build",
                                               "has_changes", "build_done",
                                               "build_failed"])
            # truncate file
            with open(fn, 'w') as fp:
                fp.write('')

        if part == -1:
            with open(fn, 'a') as fp:
                fp.flush()
            self.app.pm.db.reset_busy(builddir, "has_changes")
            if fname == "source.xml":
                # ensure that the project cache is reloaded
                self.app.pm.close_current_project(uid)
                self.app.pm.open_project(
                    uid, builddir, url_validation=ValidationMode.NO_CHECK)
                self.app.pm.set_current_project_xml(uid, fn)
            return -2

        with open(fn, 'ab') as fp:
            fp.write(binascii.a2b_base64(blob))

        return part + 1

    @rpc(String, String, Integer, _returns=String)
    @authenticated_uid
    @soap_faults
    def get_file(self, uid, builddir, filename, part):
        self.app.pm.open_project(uid, builddir)

        size = 1024 * 1024 * 5
        pos = size * part
        file_name = builddir + "/" + filename
        file_stat = os.stat(file_name)

        if pos >= file_stat.st_size:
            return "EndOfFile"

        with open(file_name, 'rb') as fp:
            if not fp:
                return "FileNotFound"
            try:
                fp.seek(pos)
                data = fp.read(size)
                return binascii.b2a_base64(data)
            except BaseException:
                return "EndOfFile"

    @rpc(String)
    @authenticated_uid
    @soap_faults
    def build_chroot_tarball(self, uid, builddir):
        self.app.pm.open_project(uid, builddir)
        self.app.pm.build_chroot_tarball(uid)

    @rpc(String)
    @authenticated_uid
    @soap_faults
    def build_sysroot(self, uid, builddir):
        self.app.pm.open_project(uid, builddir)
        self.app.pm.build_sysroot(uid)

    @rpc(String)
    @authenticated_uid
    @soap_faults
    def build_sdk(self, uid, builddir):
        self.app.pm.open_project(uid, builddir)
        self.app.pm.build_sdk(uid)

    @rpc(String, Boolean, Boolean)
    @authenticated_uid
    @soap_faults
    def build_cdroms(self, uid, builddir, build_bin, build_src):
        self.app.pm.open_project(uid, builddir)
        self.app.pm.build_cdroms(uid, build_bin, build_src)

    @rpc(String, Boolean, Boolean, Boolean)
    @authenticated_uid
    @soap_faults
    def build(self, uid, builddir, build_bin, build_src, skip_pbuilder):

        # pylint: disable=too-many-arguments

        self.app.pm.open_project(uid, builddir)
        self.app.pm.build_current_project(uid, build_bin, build_src,
                                          skip_pbuilder)

    @rpc(String, Boolean, Boolean, String)
    @authenticated_uid
    @soap_faults
    def build_pbuilder(self, uid, builddir, cross, noccache, ccachesize):
        self.app.pm.open_project(uid, builddir)
        self.app.pm.build_pbuilder(uid, cross, noccache, ccachesize)

    @rpc(String)
    @authenticated_uid
    @soap_faults
    def update_pbuilder(self, uid, builddir):
        self.app.pm.open_project(uid, builddir)
        self.app.pm.update_pbuilder(uid)

    @rpc(String)
    @authenticated_uid
    @soap_faults
    def start_cdrom(self, uid, builddir):
        self.app.pm.open_project(
            uid, builddir, url_validation=ValidationMode.NO_CHECK)

        cdrom_fname = os.path.join(builddir, "uploaded_cdrom.iso")

        # Now write empty File
        fp = open(cdrom_fname, "w")
        fp.close()

    @rpc(String, String)
    @authenticated_uid
    @soap_faults
    def append_cdrom(self, uid, builddir, data):
        self.app.pm.open_project(
            uid, builddir, url_validation=ValidationMode.NO_CHECK)

        cdrom_fname = os.path.join(builddir, "uploaded_cdrom.iso")

        # Now append data to cdrom_file
        fp = open(cdrom_fname, "ab")
        fp.write(binascii.a2b_base64(data))
        fp.close()

    @rpc(String)
    @authenticated_uid
    @soap_faults
    def finish_cdrom(self, uid, builddir):
        self.app.pm.open_project(
            uid, builddir, url_validation=ValidationMode.NO_CHECK)
        self.app.pm.set_current_project_upload_cdrom(uid)

    @rpc(String)
    @authenticated_uid
    @soap_faults
    def start_pdebuild(self, uid, builddir):
        self.app.pm.open_project(uid, builddir)

        pdebuild_fname = os.path.join(builddir, "current_pdebuild.tar.gz")

        # Now write empty File
        fp = open(pdebuild_fname, "w")
        fp.close()

    @rpc(String, String)
    @authenticated_uid
    @soap_faults
    def append_pdebuild(self, uid, builddir, data):
        self.app.pm.open_project(uid, builddir)

        pdebuild_fname = os.path.join(builddir, "current_pdebuild.tar.gz")

        # Now write empty File
        fp = open(pdebuild_fname, "ab")
        fp.write(binascii.a2b_base64(data))
        fp.close()

    @rpc(String, Integer, String, Boolean)
    @authenticated_uid
    @soap_faults
    # pylint: disable=too-many-arguments
    def finish_pdebuild(self, uid, builddir, cpuset, profile, cross):
        self.app.pm.open_project(uid, builddir)
        self.app.pm.build_current_pdebuild(uid, cpuset, profile, cross)

    @rpc(String, String)
    @authenticated_uid
    @soap_faults
    def start_upload_orig(self, uid, builddir, fname):
        self.app.pm.open_project(uid, builddir)

        orig_fname = os.path.join(builddir, fname)

        # Now write empty File
        fp = open(orig_fname, "w")
        fp.close()

        self.app.pm.set_orig_fname(uid, fname)

    @rpc(String, String)
    @authenticated_uid
    @soap_faults
    def append_upload_orig(self, uid, builddir, data):
        self.app.pm.open_project(uid, builddir)

        orig_fname = os.path.join(builddir, self.app.pm.get_orig_fname(uid))

        # Now append to File
        fp = open(orig_fname, "ab")
        fp.write(binascii.a2b_base64(data))
        fp.close()

    @rpc(String)
    @authenticated_uid
    @soap_faults
    def finish_upload_orig(self, uid, builddir):
        # If we support more than one orig, we need to put the orig_files into
        # some list here.
        # We still need the notion of a "current" orig during file upload.
        pass

    @rpc(String)
    @authenticated_uid
    @soap_faults
    def reset_project(self, uid, builddir):
        self.app.pm.open_project(uid, builddir)
        self.app.pm.db.reset_project(builddir, True)

    @rpc(String)
    @authenticated_uid
    @soap_faults
    def del_project(self, uid, builddir):
        self.app.pm.del_project(uid, builddir)

    @rpc(String, String, _returns=String)
    @authenticated_uid
    @soap_faults
    def create_project(self, uid, xml, url_validation):
        with NamedTemporaryFile() as fp:
            fp.write(binascii.a2b_base64(xml))
            fp.flush()
            prjid = self.app.pm.create_project(
                uid, fp.name, url_validation=url_validation)

        return prjid

    @rpc(_returns=String)
    @authenticated_uid
    @soap_faults
    def new_project(self, uid):
        return self.app.pm.new_project(uid)

    @rpc(String, _returns=String)
    @authenticated_uid
    @soap_faults
    def get_project_busy(self, uid, builddir):
        self.app.pm.open_project(uid, builddir)
        ret, msg = self.app.pm.current_project_is_busy(uid)
        if not msg and not ret:
            return 'ELBE-FINISH'
        return msg

    @rpc()
    @authenticated_admin
    @soap_faults
    def shutdown_initvm(self):
        # pylint: disable=no-self-use
        system("systemctl --no-block poweroff")

    @rpc(String)
    @authenticated_uid
    @soap_faults
    def rm_log(self, uid, builddir):
        self.app.pm.open_project(uid, builddir)
        self.app.pm.rm_log(uid)

    @rpc(String, _returns=String)
    @authenticated_uid
    @soap_faults
    def list_packages(self, uid, builddir):
        self.app.pm.open_project(uid, builddir)
        s = ''
        for _, _, filenames in os.walk(
                os.path.join(builddir, "repo/pool/main")):
            for filename in fnmatch.filter(filenames, '*.deb'):
                s += filename + '\n'
        return s

    @rpc(String, String)
    @authenticated_uid
    @soap_faults
    def tar_prjrepo(self, uid, builddir, filename):
        self.app.pm.open_project(uid, builddir)
        with tarfile.open(os.path.join(builddir, filename), "w:gz") as tar:
            tar.add(
                os.path.join(
                    builddir, "repo"), arcname=os.path.basename(
                    os.path.join(
                        builddir, "repo")))

    @rpc(String, String)
    @authenticated_uid
    @soap_faults
    def include_package(self, uid, builddir, filename):
        self.app.pm.open_project(uid, builddir)
        self.app.pm.add_deb_package(uid, filename)
