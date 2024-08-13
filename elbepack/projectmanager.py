# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2014-2018 Linutronix GmbH

import os
from os import path
from threading import Lock

from elbepack.asyncworker import (
    AsyncWorker,
    BuildCDROMsJob,
    BuildChrootTarJob,
    BuildJob,
    BuildSDKJob,
    BuildSysrootJob,
    CreatePbuilderJob,
    PdebuildJob,
    UpdatePbuilderJob,
)
from elbepack.db import ElbeDB
from elbepack.elbexml import ValidationMode
from elbepack.log import read_loggingQ
from elbepack.uuid7 import uuid7


class ProjectManagerError(Exception):
    pass


class AlreadyOpen(ProjectManagerError):
    def __init__(self, builddir, username):
        super().__init__(f'project in {builddir} is already opened by {username}')


class PermissionDenied(ProjectManagerError):
    def __init__(self, builddir):
        super().__init__(f'permission denied for project in {builddir}')


class NoOpenProject(ProjectManagerError):
    def __init__(self):
        super().__init__(self, 'must open a project first')


class InvalidState(ProjectManagerError):
    pass


class ProjectManager:

    def __init__(self, basepath):
        self.basepath = basepath    # Base path for new projects
        self.db = ElbeDB()          # Database of projects and users
        self.worker = AsyncWorker(self.db)
        # (userid, ElbeProject) map of open projects
        self.userid2project = {}
        self.builddir2userid = {}   # (builddir, userid) map of open projects
        self.lock = Lock()          # Lock protecting our data

    def stop(self):
        self.worker.stop()

    def new_project(self, userid):
        subdir = str(uuid7())
        builddir = path.join(self.basepath, subdir)
        self.db.create_project(builddir, owner_id=userid)
        return builddir

    def create_project(
            self,
            userid,
            xml_file,
            url_validation=ValidationMode.CHECK_ALL):
        subdir = str(uuid7())
        builddir = path.join(self.basepath, subdir)

        with self.lock:
            # Try to close old project, if any
            self._close_current_project(userid)

            self.db.create_project(builddir, owner_id=userid)

            try:
                self.db.set_xml(builddir, xml_file)
            except BaseException:
                # Delete the project, if we cannot assign an XML file
                self.db.del_project(builddir)
                raise

            # Open the new project
            ep = self.db.load_project(builddir,
                                      url_validation=url_validation)

            self.userid2project[userid] = ep
            self.builddir2userid[builddir] = userid

        return builddir

    def open_project(
            self,
            userid,
            builddir,
            url_validation=ValidationMode.CHECK_ALL,
            allow_busy=True):
        self._check_project_permission(userid, builddir)

        with self.lock:
            if builddir in self.builddir2userid:
                if self.builddir2userid[builddir] == userid:
                    # Same project selected again by the same user, don't do
                    # anything
                    ep = self.userid2project[userid]
                    if not allow_busy:
                        self._assert_not_busy(ep)
                    return ep

                # Already opened by a different user
                raise AlreadyOpen(builddir,
                                  self.db.get_username(self.builddir2userid[builddir]))

            # Try to close the old project of the user, if any
            self._close_current_project(userid)

            # Load project from the database
            ep = self.db.load_project(builddir,
                                      url_validation=url_validation)

            # Add project to our dictionaries
            self.userid2project[userid] = ep
            self.builddir2userid[builddir] = userid

            if not allow_busy:
                self._assert_not_busy(ep)
            return ep

    def close_current_project(self, userid):
        with self.lock:
            self._close_current_project(userid)

    def del_project(self, userid, builddir):
        self._check_project_permission(userid, builddir)

        with self.lock:
            # Does anyone have the project opened right now?
            if builddir in self.builddir2userid:
                if self.builddir2userid[builddir] == userid:
                    # If the calling user has opened it, then close it and
                    # proceed if closed sucessfully.
                    self._close_current_project(userid)
                else:
                    # TODO: Admin should be allowed to delete projects
                    # that are currently opened by other users
                    raise AlreadyOpen(builddir,
                                      self.db.get_username(
                                          self.builddir2userid[builddir]))

        self.db.del_project(builddir)

    def set_project_xml(self, builddir, xml_file):
        with self.lock:
            self.db.set_xml(builddir, xml_file)

    def set_upload_cdrom(self, userid, builddir, url_validation):
        ep = self.open_project(userid, builddir, url_validation, allow_busy=False)
        with self.lock:
            ep.xml.set_cdrom_mirror(
                path.join(
                    ep.builddir,
                    'uploaded_cdrom.iso'))
            ep.sync_xml_to_disk()

            # Make db reload the xml file
            self.db.set_xml(ep.builddir, None)

    def build_current_project(
            self,
            userid,
            build_bin,
            build_src,
            skip_pbuilder):
        with self.lock:
            ep = self._get_current_project(userid, allow_busy=False)
            self.worker.enqueue(BuildJob(ep, build_bin, build_src,
                                         skip_pbuilder))

    def update_pbuilder(self, userid):
        with self.lock:
            ep = self._get_current_project(userid, allow_busy=False)
            self.worker.enqueue(UpdatePbuilderJob(ep))

    def build_pbuilder(self, userid, cross, noccache, ccachesize):
        with self.lock:
            ep = self._get_current_project(userid, allow_busy=False)
            self.worker.enqueue(CreatePbuilderJob(ep, ccachesize, cross,
                                                  noccache))

    def build_current_pdebuild(self, userid, profile, cross):
        with self.lock:
            ep = self._get_current_project(userid, allow_busy=False)
            if (not path.isdir(path.join(ep.builddir, 'pbuilder')) and
                    not path.isdir(path.join(ep.builddir, 'pbuilder_cross'))):
                raise InvalidState('No pbuilder exists: run "elbe pbuilder '
                                   f'create --project {ep.builddir}" first')

            self.worker.enqueue(PdebuildJob(ep, profile, cross))

    def set_orig_fname(self, userid, fname):
        with self.lock:
            ep = self._get_current_project(userid, allow_busy=False)
            if (not path.isdir(path.join(ep.builddir, 'pbuilder')) and
                    not path.isdir(path.join(ep.builddir, 'pbuilder_cross'))):
                raise InvalidState('No pbuilder exists: run "elbe pbuilder '
                                   f'create --project {ep.builddir}" first')

            ep.orig_fname = fname
            ep.orig_files.append(fname)

    def get_orig_fname(self, userid):
        with self.lock:
            ep = self._get_current_project(userid, allow_busy=False)
            if (not path.isdir(path.join(ep.builddir, 'pbuilder')) and
                    not path.isdir(path.join(ep.builddir, 'pbuilder_cross'))):
                raise InvalidState('No pbuilder exists: run "elbe pbuilder '
                                   f'create --project {ep.builddir}" first')

            return ep.orig_fname

    def build_chroot_tarball(self, userid):
        with self.lock:
            ep = self._get_current_project(userid, allow_busy=False)
            self.worker.enqueue(BuildChrootTarJob(ep))

    def build_sysroot(self, userid):
        with self.lock:
            ep = self._get_current_project(userid, allow_busy=False)
            self.worker.enqueue(BuildSysrootJob(ep))

    def build_sdk(self, userid):
        with self.lock:
            ep = self._get_current_project(userid, allow_busy=False)
            self.worker.enqueue(BuildSDKJob(ep))

    def build_cdroms(self, userid, build_bin, build_src):
        with self.lock:
            ep = self._get_current_project(userid, allow_busy=False)
            self.worker.enqueue(BuildCDROMsJob(ep, build_bin, build_src))

    def rm_log(self, userid):
        ep = self._get_current_project(userid)
        with open(os.path.join(ep.builddir, 'log.txt'), 'wb', 0):
            pass

    def add_deb_package(self, userid, filename):
        ep = self._get_current_project(userid)

        t = os.path.splitext(filename)[1]  # filetype of uploaded file
        pkg_name = filename.split('_')[0]

        if t == '.dsc':
            ep.repo.includedsc(os.path.join(ep.builddir, filename),
                               force=True)
        elif t == '.deb':
            ep.repo.includedeb(os.path.join(ep.builddir, filename),
                               pkgname=pkg_name, force=True)
        elif t == '.changes':
            ep.repo.include(os.path.join(ep.builddir, filename),
                            force=True)

        ep.repo.finalize()

    def current_project_is_busy(self, userid):
        with self.lock:
            ep = self._get_current_project(userid)
            msg = read_loggingQ(ep.builddir)
            return self.db.is_busy(ep.builddir), msg

    def _get_current_project(self, userid, allow_busy=True):
        # Must be called with self.lock held
        if userid not in self.userid2project:
            raise NoOpenProject()

        ep = self.userid2project[userid]

        if not allow_busy:
            self._assert_not_busy(ep)

        return ep

    def _assert_not_busy(self, ep):
        if self.db.is_busy(ep.builddir):
            raise InvalidState(f'project {ep.builddir} is busy')

    def _close_current_project(self, userid):
        # Must be called with self.lock held

        if userid in self.userid2project:
            builddir = self.userid2project[userid].builddir
            if self.db.is_busy(builddir):
                raise InvalidState(
                    f'project in directory {builddir} of user '
                    f'{self.db.get_username(userid)} is '
                    'currently busy and cannot be closed')

            del self.builddir2userid[builddir]
            del self.userid2project[userid]

    def _check_project_permission(self, userid, builddir):
        if self.db.is_admin(userid):
            # Admin may access all projects
            return

        if self.db.get_owner_id(builddir) != userid:
            # Project of another user, deny access
            raise PermissionDenied(builddir)

        # User is owner, so allow it
