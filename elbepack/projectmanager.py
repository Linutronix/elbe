# ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (c) 2014-2016 Torben Hohn <torben.hohn@linutronix.de>
# Copyright (c) 2014 Stefan Gast <stefan.gast@linutronix.de>
# Copyright (c) 2014-2018 Manuel Traut <manut@linutronix.de>
# Copyright (c) 2017 Philipp Arras <philipp.arras@linutronix.de>
#
# SPDX-License-Identifier: GPL-3.0-or-later

import errno
import os

from os import path
from threading import Lock
from uuid import uuid4
from shutil import rmtree

from elbepack.db import ElbeDB, get_versioned_filename

from elbepack.asyncworker import (AsyncWorker, BuildJob, APTUpdateJob,
                                  APTCommitJob, GenUpdateJob,
                                  SaveVersionJob, CheckoutVersionJob,
                                  APTUpdUpgrJob, BuildSysrootJob,
                                  PdebuildJob, CreatePbuilderJob,
                                  UpdatePbuilderJob, BuildChrootTarJob,
                                  BuildSDKJob, BuildCDROMsJob)

from elbepack.elbexml import ValidationMode
from elbepack.log import read_loggingQ


class ProjectManagerError(Exception):
    def __init__(self, message):
        Exception.__init__(self, message)


class AlreadyOpen(ProjectManagerError):
    def __init__(self, builddir, username):
        ProjectManagerError.__init__(
            self, "project in %s is already opened by %s" %
            (builddir, username))


class PermissionDenied(ProjectManagerError):
    def __init__(self, builddir):
        ProjectManagerError.__init__(
            self, "permission denied for project in %s" %
            builddir)


class NoOpenProject(ProjectManagerError):
    def __init__(self):
        ProjectManagerError.__init__(self, "must open a project first")


class InvalidState(ProjectManagerError):
    def __init__(self, message):
        ProjectManagerError.__init__(self, message)


class OpenProjectFile(object):
    def __init__(self, pfd, mode='r'):
        self.path = path.join(pfd.builddir, pfd.name)
        self.mime_type = pfd.mime_type
        self.fobj = open(self.path, mode)


class ProjectManager(object):

    # pylint: disable=too-many-public-methods

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
        subdir = str(uuid4())
        builddir = path.join(self.basepath, subdir)
        self.db.create_project(builddir, owner_id=userid)
        return builddir

    def create_project(
            self,
            userid,
            xml_file,
            url_validation=ValidationMode.CHECK_ALL):
        subdir = str(uuid4())
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
            url_validation=ValidationMode.CHECK_ALL):
        self._check_project_permission(userid, builddir)

        with self.lock:
            if builddir in self.builddir2userid:
                if self.builddir2userid[builddir] == userid:
                    # Same project selected again by the same user, don't do
                    # anything
                    return
                else:
                    # Already opened by a different user
                    raise AlreadyOpen(builddir,
                                      self.db.get_username(
                                          self.builddir2userid[builddir]))

            # Try to close the old project of the user, if any
            self._close_current_project(userid)

            # Load project from the database
            ep = self.db.load_project(builddir,
                                      url_validation=url_validation)

            # Add project to our dictionaries
            self.userid2project[userid] = ep
            self.builddir2userid[builddir] = userid

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

    def get_current_project_data(self, userid):
        with self.lock:
            builddir = self._get_current_project(userid).builddir
            return self.db.get_project_data(builddir)

    def get_current_project_files(self, userid):
        with self.lock:
            builddir = self._get_current_project(userid).builddir
            return self.db.get_project_files(builddir)

    def open_current_project_file(self, userid, filename, mode='r'):
        with self.lock:
            builddir = self._get_current_project(
                userid, allow_busy=False).builddir

            pfd = self.db.get_project_file(builddir, filename)
            return OpenProjectFile(pfd, mode)

    def set_current_project_private_data(self, userid, private_data):
        with self.lock:
            ep = self._get_current_project(userid)
            ep.private_data = private_data

    def get_current_project_private_data(self, userid):
        private_data = None
        with self.lock:
            ep = self._get_current_project(userid)
            private_data = ep.private_data
        return private_data

    def set_current_project_xml(self, userid, xml_file):
        with self.lock:
            ep = self._get_current_project(userid, allow_busy=False)

            self.db.set_xml(ep.builddir, xml_file)

    def set_current_project_upload_cdrom(self, userid):
        with self.lock:
            ep = self._get_current_project(userid, allow_busy=False)

            ep.xml.set_cdrom_mirror(
                path.join(
                    ep.builddir,
                    'uploaded_cdrom.iso'))
            ep.sync_xml_to_disk()

            # Make db reload the xml file
            self.db.set_xml(ep.builddir, None)

    def set_current_project_postbuild(self, userid, postbuild_file):
        with self.lock:
            ep = self._get_current_project(userid, allow_busy=False)

            f = self.db.set_postbuild(ep.builddir, postbuild_file)
            ep.postbuild_file = f

    def set_current_project_savesh(self, userid, savesh_file):
        with self.lock:
            ep = self._get_current_project(userid, allow_busy=False)

            f = self.db.set_savesh(ep.builddir, savesh_file)
            ep.savesh_file = f

    def set_current_project_presh(self, userid, presh_file):
        with self.lock:
            ep = self._get_current_project(userid, allow_busy=False)

            f = self.db.set_presh(ep.builddir, presh_file)
            ep.presh_file = f

    def set_current_project_postsh(self, userid, postsh_file):
        with self.lock:
            ep = self._get_current_project(userid, allow_busy=False)

            f = self.db.set_postsh(ep.builddir, postsh_file)
            ep.postsh_file = f

    def set_current_project_version(self, userid, new_version):
        with self.lock:
            ep = self._get_current_project(userid, allow_busy=False)

            self.db.set_project_version(ep.builddir, new_version)
            ep.xml.node("/project/version").set_text(new_version)

    def list_current_project_versions(self, userid):
        with self.lock:
            ep = self._get_current_project(userid)
            return self.db.list_project_versions(ep.builddir)

    def save_current_project_version(self, userid, description=None):
        with self.lock:
            ep = self._get_current_project(userid, allow_busy=False)

            self.worker.enqueue(SaveVersionJob(ep, description))

    def checkout_project_version(self, userid, version):
        with self.lock:
            ep = self._get_current_project(userid, allow_busy=False)

            self.worker.enqueue(CheckoutVersionJob(ep, version))

    def set_current_project_version_description(self, userid, version,
                                                description):
        with self.lock:
            ep = self._get_current_project(userid)
            self.db.set_version_description(ep.builddir, version, description)

    def del_current_project_version(self, userid, version):
        with self.lock:
            ep = self._get_current_project(userid, allow_busy=False)

            name = ep.xml.text("project/name")
            self.db.del_version(ep.builddir, version)

            # Delete corresponding package archive, if existing
            pkgarchive = get_versioned_filename(name, version, ".pkgarchive")
            pkgarchive_path = path.join(ep.builddir, pkgarchive)
            try:
                rmtree(pkgarchive_path)
            except OSError as e:
                if e.errno != errno.ENOENT:
                    raise

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

    def build_pbuilder(self, userid, cross):
        with self.lock:
            ep = self._get_current_project(userid, allow_busy=False)
            self.worker.enqueue(CreatePbuilderJob(ep, cross))

    def build_current_pdebuild(self, userid, cpuset, profile, cross):
        with self.lock:
            ep = self._get_current_project(userid, allow_busy=False)
            if (not path.isdir(path.join(ep.builddir, "pbuilder")) and
                    not path.isdir(path.join(ep.builddir, "pbuilder_cross"))):
                raise InvalidState('No pbuilder exists: run "elbe pbuilder '
                                   'create --project %s" first' % ep.builddir)

            self.worker.enqueue(PdebuildJob(ep, cpuset, profile, cross))

    def set_orig_fname(self, userid, fname):
        with self.lock:
            ep = self._get_current_project(userid, allow_busy=False)
            if (not path.isdir(path.join(ep.builddir, "pbuilder")) and
                    not path.isdir(path.join(ep.builddir, "pbuilder_cross"))):
                raise InvalidState('No pbuilder exists: run "elbe pbuilder '
                                   'create --project %s" first' % ep.builddir)

            ep.orig_fname = fname
            ep.orig_files.append(fname)

    def get_orig_fname(self, userid):
        with self.lock:
            ep = self._get_current_project(userid, allow_busy=False)
            if (not path.isdir(path.join(ep.builddir, "pbuilder")) and
                    not path.isdir(path.join(ep.builddir, "pbuilder_cross"))):
                raise InvalidState('No pbuilder exists: run "elbe pbuilder '
                                   'create --project %s" first' % ep.builddir)

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

    def build_update_package(self, userid, base_version):
        with self.lock:
            c = self._get_current_project_apt_cache(userid)
            if c.get_changes():
                raise InvalidState(
                    "project %s has uncommited package changes, "
                    "please commit them first")

            ep = self._get_current_project(userid)
            self.worker.enqueue(GenUpdateJob(ep, base_version))

    def apt_upd_upgr(self, userid):
        with self.lock:
            ep = self._get_current_project(userid, allow_busy=False)
            self.worker.enqueue(APTUpdUpgrJob(ep))

    def apt_update(self, userid):
        with self.lock:
            ep = self._get_current_project(userid, allow_busy=False)
            self.worker.enqueue(APTUpdateJob(ep))

    def apt_commit(self, userid):
        with self.lock:
            ep = self._get_current_project(userid, allow_busy=False)
            self.worker.enqueue(APTCommitJob(ep))

    def apt_clear(self, userid):
        with self.lock:
            c = self._get_current_project_apt_cache(userid)
            c.clear()

    def apt_mark_install(self, userid, pkgname, version):
        with self.lock:
            c = self._get_current_project_apt_cache(userid)
            c.mark_install(pkgname, version)
            ep = self._get_current_project(userid)
            pkgs = ep.xml.get_target_packages()
            if pkgname not in pkgs:
                pkgs.append(pkgname)
            ep.xml.set_target_packages(pkgs)

    def apt_mark_upgrade(self, userid, pkgname, version):
        with self.lock:
            c = self._get_current_project_apt_cache(userid)
            c.mark_upgrade(pkgname, version)

    def get_debootstrap_pkgs(self, userid):
        with self.lock:
            ep = self._get_current_project(userid)

            debootstrap_pkgs = []
            for p in ep.xml.xml.node("debootstrappkgs"):
                debootstrap_pkgs.append(p.et.text)

            return debootstrap_pkgs

    def apt_mark_keep(self, userid, pkgname, version):
        with self.lock:
            c = self._get_current_project_apt_cache(userid)
            c.mark_keep(pkgname, version)

            ep = self._get_current_project(userid)
            pkgs = ep.xml.get_target_packages()
            if pkgname not in pkgs:
                pkgs.append(pkgname)
            ep.xml.set_target_packages(pkgs)

    def apt_get_target_packages(self, userid):
        with self.lock:
            ep = self._get_current_project(userid)
            return ep.xml.get_target_packages()

    def apt_upgrade(self, userid, dist_upgrade=False):
        with self.lock:
            c = self._get_current_project_apt_cache(userid)
            c.upgrade(dist_upgrade)

    def apt_get_changes(self, userid):
        with self.lock:
            c = self._get_current_project_apt_cache(userid)
            return c.get_changes()

    def apt_get_marked_install(self, userid, section='all'):
        with self.lock:
            c = self._get_current_project_apt_cache(userid)
            return c.get_marked_install(section=section)

    def apt_get_installed(self, userid, section='all'):
        with self.lock:
            c = self._get_current_project_apt_cache(userid)
            return c.get_installed_pkgs(section=section)

    def apt_get_upgradeable(self, userid, section='all'):
        with self.lock:
            c = self._get_current_project_apt_cache(userid)
            return c.get_upgradeable(section=section)

    def apt_get_pkglist(self, userid, section='all'):
        with self.lock:
            c = self._get_current_project_apt_cache(userid)
            return c.get_pkglist(section)

    def apt_get_pkg(self, userid, term):
        with self.lock:
            c = self._get_current_project_apt_cache(userid)
            return c.get_pkg(term)

    def apt_get_pkgs(self, userid, term):
        with self.lock:
            c = self._get_current_project_apt_cache(userid)
            return c.get_pkgs(term)

    def apt_get_sections(self, userid):
        with self.lock:
            c = self._get_current_project_apt_cache(userid)
            return c.get_sections()

    def read_current_project_log(self, userid):
        with self.lock:
            ep = self._get_current_project(userid)
            logpath = path.join(ep.builddir, "log.txt")
            f = open(logpath, "r")
        try:
            data = f.read()
        finally:
            f.close()
        return data

    def rm_log(self, userid):
        ep = self._get_current_project(userid)
        with open(os.path.join(ep.builddir, 'log.txt'), 'w', 0):
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

    def current_project_has_changes(self, userid):
        with self.lock:
            builddir = self._get_current_project(userid).builddir
            return self.db.has_changes(builddir)

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
            if self.db.is_busy(ep.builddir):
                raise InvalidState("project %s is busy" % ep.builddir)

        return ep

    def _close_current_project(self, userid):
        # Must be called with self.lock held

        if userid in self.userid2project:
            builddir = self.userid2project[userid].builddir
            if self.db.is_busy(builddir):
                raise InvalidState("project in directory %s of user %s is "
                                   "currently busy and cannot be closed" %
                                   (builddir, self.db.get_username(userid)))

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

    def _get_current_project_apt_cache(self, userid):
        # Must be called with self.lock held
        ep = self._get_current_project(userid, allow_busy=False)

        if not ep.has_full_buildenv():
            raise InvalidState(
                "project in directory %s does not have a functional "
                "build environment" % ep.builddir)

        return ep.get_rpcaptcache()
