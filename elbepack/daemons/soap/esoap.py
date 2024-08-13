# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2014-2018 Linutronix GmbH
# SPDX-FileCopyrightText: 2016 Claudius Heine <ch@denx.de>

import binascii
import fnmatch
import os
import tarfile
import traceback
from tempfile import NamedTemporaryFile

from spyne.decorator import rpc
from spyne.model.complex import Array
from spyne.model.fault import Fault
from spyne.model.primitive import Boolean, Integer, String
from spyne.service import ServiceBase

from elbepack.db import ElbeDBError, InvalidLogin
from elbepack.elbexml import ValidationError, ValidationMode
from elbepack.projectmanager import InvalidState, ProjectManagerError
from elbepack.version import elbe_version

from .authentication import SoapElbeNotAuthorized, authenticated_admin, authenticated_uid
from .datatypes import SoapFile, SoapProject


class SoapElbeDBError(Fault):
    def __init__(self, dberr):
        super().__init__(faultcode='ElbeDBError', faultstring=str(dberr))


class SoapElbeProjectError(Fault):
    def __init__(self, err):
        super().__init__(faultcode='ElbeProjectError', faultstring=str(err))


class SoapElbeValidationError(Fault):
    def __init__(self, exc):
        super().__init__(faultcode='ElbeValidationError', faultstring=exc.__repr__())


class SoapElbeInvalidState(Fault):
    def __init__(self):
        super().__init__(faultcode='ElbeInvalidState',
                         faultstring='Project is Busy ! Operation Invalid')


class ESoap (ServiceBase):

    __name__ = 'soap'

    def __init__(self):
        self.app = None
        self.transport = None

    @classmethod
    def call_wrapper(cls, ctx):
        try:
            return super().call_wrapper(ctx)
        except InvalidState:
            raise SoapElbeInvalidState()
        except ProjectManagerError as e:
            raise SoapElbeProjectError(str(e))
        except ElbeDBError as e:
            raise SoapElbeDBError(str(e))
        except OSError as e:
            raise SoapElbeProjectError('OSError: ' + str(e))
        except ValidationError as e:
            raise SoapElbeValidationError(e)
        except InvalidLogin:
            raise SoapElbeNotAuthorized()
        except Exception:
            raise SoapElbeProjectError(traceback.format_exc())

    @rpc(_returns=String)
    def get_version(self):
        return elbe_version

    @rpc(String, String, _returns=Boolean)
    def login(self, user, passwd):
        s = self.transport.req_env['beaker.session']
        s['userid'] = self.app.pm.db.validate_login(user, passwd)
        s.save()
        return True

    @rpc(_returns=Array(String))
    @authenticated_admin
    def list_users(self):
        return [u.name for u in self.app.pm.db.list_users()]

    @rpc(String, String, String, String, Boolean)
    @authenticated_admin
    def add_user(self, name, fullname, password, email, admin):

        self.app.pm.db.add_user(name, fullname, password, email, admin)

    @rpc(_returns=Array(SoapProject))
    @authenticated_admin
    def list_projects(self):
        return self.app.pm.db.list_projects()

    @rpc(String, _returns=SoapProject)
    @authenticated_uid
    def get_project(self, uid, builddir):
        self.app.pm.open_project(uid, builddir)
        return self.app.pm.db.get_project_data(builddir)

    @rpc(String, _returns=Array(SoapFile))
    @authenticated_uid
    def get_files(self, uid, builddir):
        self.app.pm.open_project(uid, builddir)
        files = self.app.pm.db.get_project_files(builddir)
        return files

    @rpc(String, String, String, Integer, _returns=Integer)
    @authenticated_uid
    def upload_file(self, uid, builddir, fname, blob, part):

        fn = os.path.join(builddir, fname)
        if part == 0:
            if self.app.pm.db.is_busy(builddir):
                return -1
            self.app.pm.db.set_busy(builddir, ['empty_project', 'needs_build',
                                               'has_changes', 'build_done',
                                               'build_failed'])
            # truncate file
            with open(fn, 'w') as fp:
                fp.write('')

        if part == -1:
            with open(fn, 'a') as fp:
                fp.flush()
            self.app.pm.db.reset_busy(builddir, 'has_changes')
            if fname == 'source.xml':
                # ensure that the project cache is reloaded
                self.app.pm.close_current_project(uid)
                self.app.pm.open_project(
                    uid, builddir, url_validation=ValidationMode.NO_CHECK)
                self.app.pm.set_project_xml(builddir, fn)
            return -2

        with open(fn, 'ab') as fp:
            fp.write(binascii.a2b_base64(blob))

        return part + 1

    @rpc(String, String, Integer, _returns=String)
    @authenticated_uid
    def get_file(self, uid, builddir, filename, part):
        self.app.pm.open_project(uid, builddir)

        size = 1024 * 1024 * 5
        pos = size * part
        file_name = builddir + '/' + filename
        file_stat = os.stat(file_name)

        if pos >= file_stat.st_size:
            return 'EndOfFile'

        with open(file_name, 'rb') as fp:
            try:
                fp.seek(pos)
                data = fp.read(size)
                return binascii.b2a_base64(data)
            except BaseException:
                return 'EndOfFile'

    @rpc(String)
    @authenticated_uid
    def build_chroot_tarball(self, uid, builddir):
        self.app.pm.open_project(uid, builddir)
        self.app.pm.build_chroot_tarball(uid)

    @rpc(String)
    @authenticated_uid
    def build_sysroot(self, uid, builddir):
        self.app.pm.open_project(uid, builddir)
        self.app.pm.build_sysroot(uid)

    @rpc(String)
    @authenticated_uid
    def build_sdk(self, uid, builddir):
        self.app.pm.open_project(uid, builddir)
        self.app.pm.build_sdk(uid)

    @rpc(String, Boolean, Boolean)
    @authenticated_uid
    def build_cdroms(self, uid, builddir, build_bin, build_src):
        self.app.pm.open_project(uid, builddir)
        self.app.pm.build_cdroms(uid, build_bin, build_src)

    @rpc(String, Boolean, Boolean, Boolean)
    @authenticated_uid
    def build(self, uid, builddir, build_bin, build_src, skip_pbuilder):

        self.app.pm.build_project(uid, builddir, build_bin, build_src, skip_pbuilder)

    @rpc(String, Boolean, Boolean, String)
    @authenticated_uid
    def build_pbuilder(self, uid, builddir, cross, noccache, ccachesize):
        self.app.pm.build_pbuilder(uid, builddir, cross, noccache, ccachesize)

    @rpc(String)
    @authenticated_uid
    def update_pbuilder(self, uid, builddir):
        self.app.pm.update_pbuilder(uid, builddir)

    @rpc(String)
    @authenticated_uid
    def start_cdrom(self, uid, builddir):
        self.app.pm.open_project(
            uid, builddir, url_validation=ValidationMode.NO_CHECK)

        cdrom_fname = os.path.join(builddir, 'uploaded_cdrom.iso')

        # Now write empty File
        fp = open(cdrom_fname, 'w')
        fp.close()

    @rpc(String, String)
    @authenticated_uid
    def append_cdrom(self, uid, builddir, data):
        self.app.pm.open_project(
            uid, builddir, url_validation=ValidationMode.NO_CHECK)

        cdrom_fname = os.path.join(builddir, 'uploaded_cdrom.iso')

        # Now append data to cdrom_file
        fp = open(cdrom_fname, 'ab')
        fp.write(binascii.a2b_base64(data))
        fp.close()

    @rpc(String)
    @authenticated_uid
    def finish_cdrom(self, uid, builddir):
        self.app.pm.set_upload_cdrom(uid, builddir, ValidationMode.NO_CHECK)

    @rpc(String)
    @authenticated_uid
    def start_pdebuild(self, uid, builddir):
        self.app.pm.open_project(uid, builddir)

        pdebuild_fname = os.path.join(builddir, 'current_pdebuild.tar.gz')

        # Now write empty File
        fp = open(pdebuild_fname, 'w')
        fp.close()

    @rpc(String, String)
    @authenticated_uid
    def append_pdebuild(self, uid, builddir, data):
        self.app.pm.open_project(uid, builddir)

        pdebuild_fname = os.path.join(builddir, 'current_pdebuild.tar.gz')

        # Now write empty File
        fp = open(pdebuild_fname, 'ab')
        fp.write(binascii.a2b_base64(data))
        fp.close()

    @rpc(String, String, Boolean)
    @authenticated_uid
    def finish_pdebuild(self, uid, builddir, profile, cross):
        self.app.pm.build_pdebuild(uid, builddir, profile, cross)

    @rpc(String, String)
    @authenticated_uid
    def start_upload_orig(self, uid, builddir, fname):
        self.app.pm.set_orig_fname(uid, builddir, fname)

    @rpc(String, String)
    @authenticated_uid
    def append_upload_orig(self, uid, builddir, data):
        self.app.pm.open_project(uid, builddir)

        orig_fname = os.path.join(builddir, self.app.pm.get_orig_fname(uid))

        # Now append to File
        fp = open(orig_fname, 'ab')
        fp.write(binascii.a2b_base64(data))
        fp.close()

    @rpc(String)
    @authenticated_uid
    def finish_upload_orig(self, uid, builddir):
        # If we support more than one orig, we need to put the orig_files into
        # some list here.
        # We still need the notion of a "current" orig during file upload.
        pass

    @rpc(String)
    @authenticated_uid
    def reset_project(self, uid, builddir):
        self.app.pm.open_project(uid, builddir)
        self.app.pm.db.reset_project(builddir, True)

    @rpc(String)
    @authenticated_uid
    def del_project(self, uid, builddir):
        self.app.pm.del_project(uid, builddir)

    @rpc(String, String, _returns=String)
    @authenticated_uid
    def create_project(self, uid, xml, url_validation):
        with NamedTemporaryFile() as fp:
            fp.write(binascii.a2b_base64(xml))
            fp.flush()
            prjid = self.app.pm.create_project(
                uid, fp.name, url_validation=url_validation)

        return prjid

    @rpc(_returns=String)
    @authenticated_uid
    def new_project(self, uid):
        return self.app.pm.new_project(uid)

    @rpc(String, _returns=String)
    @authenticated_uid
    def get_project_busy(self, uid, builddir):
        self.app.pm.open_project(uid, builddir)
        ret, msg = self.app.pm.current_project_is_busy(uid)
        if not msg and not ret:
            return 'ELBE-FINISH'
        return msg

    @rpc(String)
    @authenticated_uid
    def rm_log(self, uid, builddir):
        self.app.pm.open_project(uid, builddir)
        self.app.pm.rm_log(uid)

    @rpc(String, _returns=String.customize(max_occurs='unbounded'))
    @authenticated_uid
    def list_packages(self, uid, builddir):
        self.app.pm.open_project(uid, builddir)
        r = []
        for _, _, filenames in os.walk(
                os.path.join(builddir, 'repo/pool/main')):
            for filename in fnmatch.filter(filenames, '*.deb'):
                r.append(filename)
        return sorted(r)

    @rpc(String, String)
    @authenticated_uid
    def tar_prjrepo(self, uid, builddir, filename):
        self.app.pm.open_project(uid, builddir)
        with tarfile.open(os.path.join(builddir, filename), 'w:gz') as tar:
            tar.add(
                os.path.join(
                    builddir, 'repo'), arcname=os.path.basename(
                    os.path.join(
                        builddir, 'repo')))

    @rpc(String, String)
    @authenticated_uid
    def include_package(self, uid, builddir, filename):
        self.app.pm.open_project(uid, builddir)
        self.app.pm.add_deb_package(uid, filename)
