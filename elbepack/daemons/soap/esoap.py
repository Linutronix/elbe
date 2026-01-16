# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2014-2018 Linutronix GmbH
# SPDX-FileCopyrightText: 2016 Claudius Heine <ch@denx.de>

import binascii
import fnmatch
import os
import tarfile
import traceback
from base64 import b85encode
from tempfile import NamedTemporaryFile

from spyne.decorator import rpc
from spyne.model.complex import Array
from spyne.model.fault import Fault
from spyne.model.primitive import Boolean, Integer, String
from spyne.service import ServiceBase

from elbepack.db import ElbeDBError, InvalidLogin
from elbepack.elbexml import ValidationError, ValidationMode
from elbepack.projectmanager import InvalidState, ProjectManagerError
from elbepack.version import elbe_version, is_devel

from .datatypes import ServerStatus, SoapFile, SoapProject


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


class SoapElbeNotAuthorized(Fault):
    def __init__(self):
        Fault.__init__(
            self,
            faultcode='ElbeNotAuthorized',
            faultstring='Not Authorized ! Cant let you perform this command.')


def _linux_meminfo():
    r = {}

    with open('/proc/meminfo', 'r') as f:
        for line in f.readlines():
            k, v = line.split(':', maxsplit=1)
            v = v.strip()

            if v.endswith(' kB'):
                v = v[:-3]
                v = int(v)
                v *= 1024
            else:
                v = int(v)

            r[k] = v

    return r


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

    @rpc(_returns=Array(SoapProject))
    def list_projects(self):
        return self.app.pm.db.list_projects()

    @rpc(String, _returns=SoapProject)
    def get_project(self, builddir):
        return self.app.pm.db.get_project_data(builddir)

    @rpc(String, _returns=Array(SoapFile))
    def get_files(self, builddir):
        files = self.app.pm.db.get_project_files(builddir)
        return files

    @rpc(String, String, String, Integer, _returns=Integer)
    def upload_file(self, builddir, fname, blob, part):

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
                self.app.pm.open_project(builddir, url_validation=ValidationMode.NO_CHECK)
                self.app.pm.set_project_xml(builddir, fn)
            return -2

        with open(fn, 'ab') as fp:
            fp.write(binascii.a2b_base64(blob))

        return part + 1

    @rpc(String)
    def build_chroot_tarball(self, builddir):
        self.app.pm.build_chroot_tarball(builddir)

    @rpc(String)
    def build_sysroot(self, builddir):
        self.app.pm.build_sysroot(builddir)

    @rpc(String)
    def build_sdk(self, builddir):
        self.app.pm.build_sdk(builddir)

    @rpc(String, Boolean, Boolean)
    def build_cdroms(self, builddir, build_bin, build_src):
        self.app.pm.build_cdroms(builddir, build_bin, build_src)

    @rpc(String, Boolean, Boolean, Boolean)
    def build(self, builddir, build_bin, build_src, skip_pbuilder):

        self.app.pm.build_project(builddir, build_bin, build_src, skip_pbuilder)

    @rpc(String, Boolean, Boolean, String)
    def build_pbuilder(self, builddir, cross, noccache, ccachesize):
        self.app.pm.build_pbuilder(builddir, cross, noccache, ccachesize)

    @rpc(String)
    def update_pbuilder(self, builddir):
        self.app.pm.update_pbuilder(builddir)

    @rpc(String, String, String)
    def append_to_file(self, builddir, filename, data):
        with open(os.path.join(builddir, filename), 'ab') as f:
            f.write(binascii.a2b_base64(data))

    @rpc(String, _returns=String)
    def start_cdrom(self, builddir):
        fname = 'uploaded_cdrom.iso'

        with open(os.path.join(builddir, fname), 'w'):
            # Now write empty File
            pass

        return fname

    @rpc(String)
    def finish_cdrom(self, builddir):
        self.app.pm.set_upload_cdrom(builddir, ValidationMode.NO_CHECK)

    @rpc(String, _returns=String)
    def start_pdebuild(self, builddir):
        fname = 'current_pdebuild.tar.gz'
        with open(os.path.join(builddir, fname), 'w'):
            # Now write empty File
            pass

        return fname

    @rpc(String, String, Boolean)
    def finish_pdebuild(self, builddir, profile, cross):
        self.app.pm.build_pdebuild(builddir, profile, cross)

    @rpc(String, String, _returns=String)
    def start_upload_orig(self, builddir, fname):
        self.app.pm.add_orig_fname(builddir, fname)
        return fname

    @rpc(String)
    def finish_upload_orig(self, builddir):
        pass

    @rpc(String)
    def reset_project(self, builddir):
        self.app.pm.db.reset_project(builddir, True)

    @rpc(String)
    def del_project(self, builddir):
        self.app.pm.del_project(builddir)

    @rpc(String, String, _returns=String)
    def create_project(self, xml, url_validation):
        with NamedTemporaryFile() as fp:
            fp.write(binascii.a2b_base64(xml))
            fp.flush()
            prjid = self.app.pm.create_project(
                fp.name, url_validation=url_validation)

        return prjid

    @rpc(_returns=String)
    def new_project(self):
        return self.app.pm.new_project()

    @rpc(String, _returns=String)
    def get_project_busy(self, builddir):
        ret, msg = self.app.pm.project_is_busy(builddir)
        if not msg and not ret:
            return 'ELBE-FINISH'
        return b85encode(msg.encode('utf-8'))

    @rpc(String)
    def rm_log(self, builddir):
        self.app.pm.rm_log(builddir)

    @rpc(String, _returns=String.customize(max_occurs='unbounded'))
    def list_packages(self, builddir):
        r = []
        for _, _, filenames in os.walk(
                os.path.join(builddir, 'repo/pool/main')):
            for filename in fnmatch.filter(filenames, '*.deb'):
                r.append(filename)
        return sorted(r)

    @rpc(String, String)
    def tar_prjrepo(self, builddir, filename):
        with tarfile.open(os.path.join(builddir, filename), 'w:gz') as tar:
            tar.add(
                os.path.join(
                    builddir, 'repo'), arcname=os.path.basename(
                    os.path.join(
                        builddir, 'repo')))

    @rpc(String, String)
    def include_package(self, builddir, filename):
        self.app.pm.add_deb_package(builddir, filename)

    @rpc(_returns=ServerStatus)
    def status(self):
        meminfo = _linux_meminfo()

        return ServerStatus(
            version=elbe_version,
            is_devel=is_devel,
            storage_free_bytes=self.app.pm.storage_free_bytes(),
            memory_total_bytes=meminfo['MemTotal'],
            memory_available_bytes=meminfo['MemAvailable'],
            orphan_project_directories=self.app.pm.orphan_project_directories(),
        )
