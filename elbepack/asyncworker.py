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

from threading import Thread
from Queue import Queue
from os import path, getcwd, chdir
from contextlib import contextmanager
from urllib import quote
import traceback

from elbepack.db import get_versioned_filename
from elbepack.dump import dump_fullpkgs
from elbepack.updatepkg import gen_update_pkg
from elbepack.pkgarchive import gen_binpkg_archive, checkout_binpkg_archive
from elbepack.rfs import DebootstrapException
from elbepack.elbeproject import AptCacheCommitError, AptCacheUpdateError


class AsyncWorkerJob(object):
    def __init__(self, project):
        self.project = project

    def enqueue(self, queue, db):
        queue.put(self)

    def execute(self, db):
        pass


class BuildSysrootJob(AsyncWorkerJob):
    def __init__(self, project):
        AsyncWorkerJob.__init__(self, project)

    def enqueue(self, queue, db):
        db.set_busy(self.project.builddir,
                    ["empty_project", "needs_build", "has_changes",
                     "build_done", "build_failed"])
        self.project.log.printo("Enqueueing project for building sysroot")
        AsyncWorkerJob.enqueue(self, queue, db)

    def execute(self, db):
        try:
            self.project.log.printo("Build sysroot started")
            self.project.build_sysroot()
            db.update_project_files(self.project)
            self.project.log.printo("Build finished successfully")
            db.reset_busy(self.project.builddir, "build_done")
        except Exception as e:
            db.update_project_files(self.project)
            self.project.log.printo("Build sysroot failed")
            self.project.log.printo(traceback.format_exc())
            db.reset_busy(self.project.builddir, "build_failed")


class BuildChrootTarJob(AsyncWorkerJob):
    def __init__(self, project):
        AsyncWorkerJob.__init__(self, project)

    def enqueue(self, queue, db):
        db.set_busy(self.project.builddir,
                    ["empty_project", "needs_build", "has_changes",
                     "build_done", "build_failed"])
        self.project.log.printo("Enqueueing project for building croot tar")
        AsyncWorkerJob.enqueue(self, queue, db)

    def execute(self, db):
        try:
            self.project.log.printo("Build chroot tarball started")
            self.project.build_chroottarball()
            db.update_project_files(self.project)
            self.project.log.printo("Build finished successfully")
            db.reset_busy(self.project.builddir, "build_done")
        except Exception as e:
            db.update_project_files(self.project)
            self.project.log.printo("Build chrroot tarball failed")
            self.project.log.printo(traceback.format_exc())
            db.reset_busy(self.project.builddir, "build_failed")


class BuildJob(AsyncWorkerJob):
    def __init__(self, project, build_bin, build_src, skip_pbuilder):
        AsyncWorkerJob.__init__(self, project)
        self.build_bin = build_bin
        self.build_src = build_src
        self.skip_pbuilder = skip_pbuilder

    def enqueue(self, queue, db):
        db.set_busy(self.project.builddir,
                    ["empty_project", "needs_build", "has_changes",
                     "build_done", "build_failed"])
        self.project.log.printo("Enqueueing project for build")
        AsyncWorkerJob.enqueue(self, queue, db)

    def execute(self, db):
        try:
            self.project.log.printo("Build started")
            self.project.build(skip_pkglist=False,
                               build_bin=self.build_bin,
                               build_sources=self.build_src,
                               skip_pbuild=self.skip_pbuilder)
            db.update_project_files(self.project)
            self.project.log.printo("Build finished successfully")
            db.reset_busy(self.project.builddir, "build_done")
        except DebootstrapException as e:
            db.update_project_files(self.project)
            self.project.log.printo("Build failed !!!")
            self.project.log.printo("")
            self.project.log.printo(
                "Debootstrap failed to install the base rootfilesystem.")
            self.project.log.printo("Probable cause might be:")
            self.project.log.printo("- Problems with Internet Connection")
            self.project.log.printo("- Broken mirrors")
            self.project.log.printo("")
            self.project.log.printo("Message from apt:")
            self.project.log.printo(str(e))
            self.project.log.printo("")
            db.reset_busy(self.project.builddir, "build_failed")
        except AptCacheCommitError as e:
            db.update_project_files(self.project)
            self.project.log.printo("Build failed !!!")
            self.project.log.printo("")
            self.project.log.printo("Failed to commit the AptCache changes.")
            self.project.log.printo(
                "Most likely is, that packages failed to download.")
            self.project.log.printo("Probable cause might be:")
            self.project.log.printo("- Problems with Internet Connection")
            self.project.log.printo("- Broken mirrors")
            self.project.log.printo("")
            self.project.log.printo("Message from apt:")
            self.project.log.printo(str(e))
            self.project.log.printo("")
            db.reset_busy(self.project.builddir, "build_failed")
        except AptCacheUpdateError as e:
            db.update_project_files(self.project)
            self.project.log.printo("Build failed !!!")
            self.project.log.printo("")
            self.project.log.printo("Failed to build the Apt Cache.")
            self.project.log.printo(
                "Not all Mirror Index Files could be downloaded.")
            self.project.log.printo("Probable cause might be:")
            self.project.log.printo("- Problems with Internet Connection")
            self.project.log.printo("- Broken mirrors")
            self.project.log.printo("")
            self.project.log.printo("Message from apt:")
            self.project.log.printo(str(e))
            self.project.log.printo("")
            db.reset_busy(self.project.builddir, "build_failed")
        except Exception as e:
            db.update_project_files(self.project)
            self.project.log.printo("Build failed")
            self.project.log.printo(traceback.format_exc())
            self.project.log.printo("")
            self.project.log.printo("Exception:")
            self.project.log.printo(str(e))
            self.project.log.printo("")
            db.reset_busy(self.project.builddir, "build_failed")


class PdebuildJob(AsyncWorkerJob):
    def __init__(self, project):
        AsyncWorkerJob.__init__(self, project)

    def enqueue(self, queue, db):
        db.set_busy(self.project.builddir,
                    ["empty_project", "needs_build", "has_changes",
                     "build_done", "build_failed"])
        self.project.log.printo("Enqueueing project for pdebuild")
        AsyncWorkerJob.enqueue(self, queue, db)

    def execute(self, db):
        try:
            self.project.log.printo("Pdebuild started")
            self.project.pdebuild()
            db.update_project_files(self.project)
            self.project.log.printo("Pdeb finished successfully")
            db.reset_busy(self.project.builddir, "build_done")
        except Exception as e:
            db.update_project_files(self.project)
            self.project.log.printo("Pdebuild failed")
            self.project.log.printo(traceback.format_exc())
            db.reset_busy(self.project.builddir, "build_failed")


class CreatePbuilderJob(AsyncWorkerJob):
    def __init__(self, project):
        AsyncWorkerJob.__init__(self, project)

    def enqueue(self, queue, db):
        db.set_busy(self.project.builddir,
                    ["empty_project", "needs_build", "has_changes",
                     "build_done", "build_failed"])
        self.project.log.printo(
            "Enqueueing project to have the pbuilder built")
        AsyncWorkerJob.enqueue(self, queue, db)

    def execute(self, db):
        try:
            self.project.log.printo("Building pbuilder started")
            self.project.create_pbuilder()
            db.update_project_files(self.project)
            self.project.log.printo("Pbuilder finished successfully")
            db.reset_busy(self.project.builddir, "build_done")
        except Exception as e:
            db.update_project_files(self.project)
            self.project.log.printo("Pbuilder failed")
            self.project.log.printo(traceback.format_exc())
            db.reset_busy(self.project.builddir, "build_failed")


class UpdatePbuilderJob(AsyncWorkerJob):
    def __init__(self, project):
        AsyncWorkerJob.__init__(self, project)

    def enqueue(self, queue, db):
        db.set_busy(self.project.builddir,
                    ["empty_project", "needs_build", "has_changes",
                     "build_done", "build_failed"])
        self.project.log.printo("Enqueueing project to update the pbuilder")
        AsyncWorkerJob.enqueue(self, queue, db)

    def execute(self, db):
        try:
            self.project.log.printo("Updating pbuilder started")
            self.project.update_pbuilder()
            self.project.log.printo("Updating Pbuilder finished successfully")
            db.reset_busy(self.project.builddir, "build_done")
        except Exception as e:
            db.update_project_files(self.project)
            self.project.log.printo("update Pbuilder failed")
            self.project.log.printo(traceback.format_exc())
            db.reset_busy(self.project.builddir, "build_failed")


class APTUpdateJob(AsyncWorkerJob):
    def __init__(self, project):
        AsyncWorkerJob.__init__(self, project)

    def enqueue(self, queue, db):
        db.set_busy(self.project.builddir,
                    ["build_done", "has_changes"])
        self.project.log.printo("Enqueueing project for APT cache update")
        AsyncWorkerJob.enqueue(self, queue, db)

    def execute(self, db):
        try:
            self.project.log.printo("APT cache update started")
            with self.project.buildenv:
                self.project.get_rpcaptcache().update()
            self.project.log.printo("APT cache update finished successfully")
            db.reset_busy(self.project.builddir,
                          "has_changes")
        except Exception as e:
            self.project.log.printo("APT cache update failed")
            self.project.log.printo(str(e))
            db.reset_busy(self.project.builddir, "build_failed")


class APTUpdUpgrJob(AsyncWorkerJob):
    def __init__(self, project):
        AsyncWorkerJob.__init__(self, project)

    def enqueue(self, queue, db):
        db.set_busy(self.project.builddir, ["build_done", "has_changes"])
        self.project.log.printo("Enqueueing project for APT update & upgrade")
        AsyncWorkerJob.enqueue(self, queue, db)

    def execute(self, db):
        try:
            self.project.log.printo("APT update started")
            with self.project.buildenv:
                self.project.get_rpcaptcache().update()
            self.project.log.printo("APT update finished, upgrade started")
            self.project.get_rpcaptcache().upgrade()
            self.project.log.printo("APT upgrade finished")
            db.reset_busy(self.project.builddir, "has_changes")
        except Exception as e:
            self.project.log.printo("APT update & upgrade failed")
            self.project.log.printo(str(e))
            db.reset_busy(self.project.builddir, "build_failed")


class APTCommitJob(AsyncWorkerJob):
    def __init__(self, project):
        AsyncWorkerJob.__init__(self, project)

    def enqueue(self, queue, db):
        old_status = db.set_busy(self.project.builddir,
                                 ["build_done", "has_changes"])
        if self.project.get_rpcaptcache().get_changes():
            self.project.log.printo("Enqueueing project for package changes")
            AsyncWorkerJob.enqueue(self, queue, db)
        else:
            db.reset_busy(self.project.builddir, old_status)

    def execute(self, db):
        try:
            self.project.log.printo("Applying package changes")
            with self.project.buildenv:
                # Commit changes, update full package list and write
                # out new source.xml
                self.project.get_rpcaptcache().commit()
                dump_fullpkgs(self.project.xml,
                              self.project.buildenv.rfs,
                              self.project.get_rpcaptcache())

            sourcexmlpath = path.join(self.project.builddir,
                                      "source.xml")
            self.project.xml.xml.write(sourcexmlpath)

            self.project.log.printo("Package changes applied successfully")
            db.reset_busy(self.project.builddir,
                          "has_changes")
        except Exception as e:
            self.project.log.printo("Applying package changes failed")
            self.project.log.printo(str(e))
            db.reset_busy(self.project.builddir,
                          "build_failed")


class GenUpdateJob(AsyncWorkerJob):
    def __init__(self, project, base_version):
        self.name = project.xml.text("/project/name")
        self.base_version = base_version
        self.current_version = project.xml.text("/project/version")
        AsyncWorkerJob.__init__(self, project)

    def enqueue(self, queue, db):
        self.old_status = db.set_busy(self.project.builddir,
                                      ["build_done", "has_changes"])
        self.base_version_xml = db.get_version_xml(self.project.builddir,
                                                   self.base_version)

        self.project.log.printo(
            "Enqueueing project for generating update package")

        AsyncWorkerJob.enqueue(self, queue, db)

    def execute(self, db):
        upd_filename = self._gen_upd_filename()
        upd_pathname = path.join(self.project.builddir, upd_filename)

        self.project.log.printo("Generating update package")

        try:
            gen_update_pkg(self.project, self.base_version_xml, upd_pathname)
            self.project.log.printo("Update package generated successfully")
        except Exception as e:
            self.project.log.printo("Generating update package failed")
            self.project.log.printo(str(e))
        finally:
            # Update generation does not change the project, so we always
            # keep the old status
            db.add_project_file(self.project.builddir, upd_filename,
                                "application/octet-stream",
                                "Update package from %s to %s" %
                                (self.base_version, self.current_version))
            db.reset_busy(self.project.builddir, self.old_status)

    def _gen_upd_filename(self):
        filename = quote(self.name, ' ') + '_'
        filename += quote(self.base_version) + '_'
        filename += quote(self.current_version) + '.upd'

        return filename


class SaveVersionJob(AsyncWorkerJob):
    def __init__(self, project, description):
        AsyncWorkerJob.__init__(self, project)
        self.description = description

    def enqueue(self, queue, db):
        self.old_status = db.set_busy(self.project.builddir,
                                      ["build_done", "has_changes"])
        self.name = self.project.xml.text("project/name")
        self.version = self.project.xml.text("project/version")

        # Create the database entry now. This has the advantage that the
        # user will see an error message immediately, if he tries to use
        # the same version number twice. The time-consuming part is creating
        # the package archive, which is done in execute.
        try:
            db.save_version(self.project.builddir, self.description)
        except BaseException:
            db.reset_busy(self.project.builddir, self.old_status)
            raise

        if self.project.savesh_file:
            self.project.log.h2("save version script:")
            self.project.log.do(self.project.savesh_file + ' "%s %s %s"' % (
                self.project.builddir,
                self.project.xml.text("project/version"),
                self.project.xml.text("project/name")),
                allow_fail=True)

        self.project.log.printo("Enqueueing project to save package archive")
        AsyncWorkerJob.enqueue(self, queue, db)

    def execute(self, db):
        self.project.log.printo("Generating package archive")
        repodir = get_versioned_filename(self.name, self.version,
                                         ".pkgarchive")
        try:
            gen_binpkg_archive(self.project, repodir)
            self.project.log.printo("Version saved successfully")
        except Exception as e:
            db.del_version(self.project.builddir, self.version, force=True)
            self.project.log.printo("Saving version failed")
            self.project.log.printo(str(e))
        finally:
            db.reset_busy(self.project.builddir, self.old_status)


class CheckoutVersionJob(AsyncWorkerJob):
    def __init__(self, project, version):
        AsyncWorkerJob.__init__(self, project)
        self.version = version

    def enqueue(self, queue, db):
        self.name = self.project.xml.text("project/name")
        old_status = db.set_busy(self.project.builddir,
                                 ["build_done", "has_changes", "build_failed"])

        # If old status was build_failed, just restore the source.xml of the
        # given version and restore the status, indicating that we need a
        # complete rebuild
        if old_status == "build_failed":
            self.project.log.printo("Previous project status indicated a "
                                    "failed build.")
            self.project.log.printo("Just checking out the XML file.")

            try:
                db.checkout_version_xml(self.project.builddir, self.version)
                self.project.set_xml(None)
            finally:
                db.reset_busy(self.project.builddir, old_status)
            return

        # Otherwise, restore the source.xml of the given version and enqueue
        # the project for package archive checkout
        try:
            db.checkout_version_xml(self.project.builddir, self.version)
            self.project.set_xml(None)
        except BaseException:
            db.reset_busy(self.project.builddir, old_status)
            self.project.set_xml(None)
            raise

        self.project.log.printo(
            "Enqueueing project for package archive checkout")
        AsyncWorkerJob.enqueue(self, queue, db)

    def execute(self, db):
        self.project.log.printo("Checking out package archive")
        repodir = get_versioned_filename(self.name, self.version,
                                         ".pkgarchive")

        try:
            checkout_binpkg_archive(self.project, repodir)
            self.project.log.printo(
                "Package archive checked out successfully")
            db.reset_busy(self.project.builddir, "has_changes")
        except Exception as e:
            self.project.log.printo(
                "Checking out package archive failed")
            self.project.log.printo(str(e))
            db.reset_busy(self.project.builddir, "build_failed")


@contextmanager
def savecwd():
    oldcwd = getcwd()
    try:
        yield
    finally:
        chdir(oldcwd)


class AsyncWorker(Thread):
    def __init__(self, db):
        Thread.__init__(self, name="AsyncWorker")
        self.db = db
        self.queue = Queue()
        self.start()

    def stop(self):
        self.queue.put(None)
        self.queue.join()
        self.join()

    def enqueue(self, job):
        job.enqueue(self.queue, self.db)

    def run(self):
        loop = True
        while loop:
            job = self.queue.get()
            if job is not None:
                with savecwd():
                    job.execute(self.db)
            else:
                loop = False
            self.queue.task_done()
