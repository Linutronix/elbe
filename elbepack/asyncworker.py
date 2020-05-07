# ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (c) 2014-2015 Torben Hohn <torben.hohn@linutronix.de>
# Copyright (c) 2014 Stefan Gast <stefan.gast@linutronix.de>
# Copyright (c) 2015-2018 Manuel Traut <manut@linutronix.de>
#
# SPDX-License-Identifier: GPL-3.0-or-later

from threading import Thread
from os import path, getcwd, chdir
from contextlib import contextmanager
import logging

from elbepack.db import get_versioned_filename
from elbepack.dump import dump_fullpkgs
from elbepack.updatepkg import gen_update_pkg
from elbepack.pkgarchive import gen_binpkg_archive, checkout_binpkg_archive
from elbepack.rfs import DebootstrapException
from elbepack.elbeproject import AptCacheCommitError, AptCacheUpdateError
from elbepack.shellhelper import do
from elbepack.log import elbe_logging, read_maxlevel, reset_level

try:
    from Queue import Queue
    from urllib import quote
except ImportError:
    from queue import Queue
    from urllib.parse import quote

class AsyncWorkerJob(object):

    build_done   = "build_done"
    build_failed = "build_failed"
    has_changes  = "has_changes"

    def __init__(self, project):
        self.project = project

    def enqueue(self, queue, db):
        reset_level(self.project.builddir)
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
        logging.info("Enqueueing project for building sysroot")
        AsyncWorkerJob.enqueue(self, queue, db)

    def execute(self, db):
        success = self.build_failed
        try:
            logging.info("Build sysroot started")
            self.project.build_sysroot()
            db.update_project_files(self.project)
        except Exception:
            logging.exception("Build sysroot failed")
        else:
            if read_maxlevel(self.project.builddir) >= logging.ERROR:
                logging.info("Build finished with Error")
            else:
                logging.info("Build finished successfully")
                success = self.build_done
        finally:
            db.update_project_files(self.project)
            db.reset_busy(self.project.builddir, success)


class BuildSDKJob(AsyncWorkerJob):
    def __init__(self, project):
        AsyncWorkerJob.__init__(self, project)

    def enqueue(self, queue, db):
        db.set_busy(self.project.builddir,
                    ["empty_project", "needs_build", "has_changes",
                     "build_done", "build_failed"])
        logging.info("Enqueueing project for building SDK")
        AsyncWorkerJob.enqueue(self, queue, db)

    def execute(self, db):
        success = self.build_failed
        try:
            logging.info("Build SDK started")
            self.project.build_sdk()
        except Exception:
            logging.exception("Build SDK Failed")
        else:
            if read_maxlevel(self.project.builddir) >= logging.ERROR:
                logging.info("Build finished with Error")
            else:
                logging.info("Build finished successfully")
                success = self.build_done
        finally:
            db.update_project_files(self.project)
            db.reset_busy(self.project.builddir, success)


class BuildCDROMsJob(AsyncWorkerJob):
    def __init__(self, project, build_bin, build_src):
        AsyncWorkerJob.__init__(self, project)
        self.build_bin = build_bin
        self.build_src = build_src

    def enqueue(self, queue, db):
        db.set_busy(self.project.builddir,
                    ["empty_project", "needs_build", "has_changes",
                     "build_done", "build_failed"])
        logging.info("Enqueueing project for building CDROMs")
        AsyncWorkerJob.enqueue(self, queue, db)

    def execute(self, db):
        success = self.build_failed
        try:
            logging.info("Build CDROMs started")
            self.project.build_cdroms(self.build_bin, self.build_src)
        except Exception:
            logging.exception("Build CDROMs failed")
        else:
            if read_maxlevel(self.project.builddir) >= logging.ERROR:
                logging.info("Build finished with Error")
            else:
                logging.info("Build finished successfully")
                success = self.build_done
        finally:
            db.update_project_files(self.project)
            db.reset_busy(self.project.builddir, success)

class BuildChrootTarJob(AsyncWorkerJob):
    def __init__(self, project):
        AsyncWorkerJob.__init__(self, project)

    def enqueue(self, queue, db):
        db.set_busy(self.project.builddir,
                    ["empty_project", "needs_build", "has_changes",
                     "build_done", "build_failed"])
        logging.info("Enqueueing project for building croot tar")
        AsyncWorkerJob.enqueue(self, queue, db)

    def execute(self, db):
        success = self.build_failed
        try:
            logging.info("Build chroot tarball started")
            self.project.build_chroottarball()
        except Exception:
            logging.exception("Build chrroot tarball failed")
        else:
            if read_maxlevel(self.project.builddir) >= logging.ERROR:
                logging.info("Build finished with Error")
            else:
                logging.info("Build finished successfully")
                success = self.build_done
        finally:
            db.update_project_files(self.project)
            db.reset_busy(self.project.builddir, success)


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
        logging.info("Enqueueing project for build")
        AsyncWorkerJob.enqueue(self, queue, db)

    def execute(self, db):

        success = self.build_failed
        try:
            logging.info("Build started")
            self.project.build(skip_pkglist=False,
                               build_bin=self.build_bin,
                               build_sources=self.build_src,
                               skip_pbuild=self.skip_pbuilder)
        except (DebootstrapException, AptCacheCommitError, AptCacheUpdateError) as e:
            if isinstance(e, DebootstrapException):
                err = "Debootstrap failed to install the base rootfilesystem."
            elif isinstance(e, AptCacheCommitError):
                err = "Failed to commit the AptCache changes."
            elif isinstance(e, AptCacheUpdateError):
                err ="Failed to build the Apt Cache."

            logging.exception("%s\n"
                              "Probable cause might be:\n"
                              "  - Problems with internet connection\n"
                              "  - Broken mirrors\n", err)
        except Exception:
            logging.exception("Build failed")
        else:
            if read_maxlevel(self.project.builddir) >= logging.ERROR:
                logging.info("Build finished with Error")
            else:
                logging.info("Build finished successfully")
                success = self.build_done
        finally:
            db.update_project_files(self.project)
            db.reset_busy(self.project.builddir, success)

class PdebuildJob(AsyncWorkerJob):
    def __init__(self, project, cpuset=-1, profile="", cross=False):
        AsyncWorkerJob.__init__(self, project)
        self.cpuset=cpuset
        self.profile=profile
        self.cross=cross

    def enqueue(self, queue, db):
        db.set_busy(self.project.builddir,
                    ["empty_project", "needs_build", "has_changes",
                     "build_done", "build_failed"])
        logging.info("Enqueueing project for pdebuild")
        AsyncWorkerJob.enqueue(self, queue, db)

    def execute(self, db):
        success = self.build_failed
        try:
            logging.info("Pdebuild started")
            self.project.pdebuild(self.cpuset, self.profile, self.cross)
        except Exception:
            logging.exception("Pdebuild failed")
        else:
            if read_maxlevel(self.project.builddir) >= logging.ERROR:
                logging.info("Pdeb finished with Error")
            else:
                logging.info("Pdeb finished successfully")
                success = self.build_done
        finally:
            db.update_project_files(self.project)
            db.reset_busy(self.project.builddir, success)

class CreatePbuilderJob(AsyncWorkerJob):
    def __init__(self, project, cross=False):
        AsyncWorkerJob.__init__(self, project)
        self.cross = cross

    def enqueue(self, queue, db):
        db.set_busy(self.project.builddir,
                    ["empty_project", "needs_build", "has_changes",
                     "build_done", "build_failed"])
        logging.info("Enqueueing project to have the pbuilder built")
        AsyncWorkerJob.enqueue(self, queue, db)

    def execute(self, db):
        success = self.build_failed
        try:
            logging.info("Building pbuilder started")
            self.project.create_pbuilder(self.cross)
        except Exception:
            logging.exception("Pbuilder failed")
        else:
            logging.info("Pbuilder finished successfully")
            success = self.build_done
        finally:
            db.update_project_files(self.project)
            db.reset_busy(self.project.builddir, success)


class UpdatePbuilderJob(AsyncWorkerJob):
    def __init__(self, project):
        AsyncWorkerJob.__init__(self, project)

    def enqueue(self, queue, db):
        db.set_busy(self.project.builddir,
                    ["empty_project", "needs_build", "has_changes",
                     "build_done", "build_failed"])
        logging.info("Enqueueing project to update the pbuilder")
        AsyncWorkerJob.enqueue(self, queue, db)

    def execute(self, db):
        success = self.build_done
        try:
            logging.info("Updating pbuilder started")
            self.project.update_pbuilder()
        except Exception:
            db.update_project_files(self.project)
            logging.exception("update Pbuilder failed")
        else:
            if read_maxlevel(self.project.builddir) >= logging.ERROR:
                logging.info("Updating Pbuilder finished with Error")
            else:
                logging.info("Updating Pbuilder finished successfully")
                success = self.build_done
        finally:
            db.reset_busy(self.project.builddir, success)


class APTUpdateJob(AsyncWorkerJob):
    def __init__(self, project):
        AsyncWorkerJob.__init__(self, project)

    def enqueue(self, queue, db):
        db.set_busy(self.project.builddir,
                    ["build_done", "has_changes"])
        logging.info("Enqueueing project for APT cache update")
        AsyncWorkerJob.enqueue(self, queue, db)

    def execute(self, db):
        success = self.build_failed
        try:
            logging.info("APT cache update started")
            with self.project.buildenv:
                self.project.get_rpcaptcache().update()
        except Exception:
            logging.exception("APT cache update failed")
        else:
            if read_maxlevel(self.project.builddir) >= logging.ERROR:
                logging.info("APT cache update finished with Error")
            else:
                logging.info("APT cache update finished successfully")
                success = self.has_changes
        finally:
            db.reset_busy(self.project.builddir, success)

class APTUpdUpgrJob(AsyncWorkerJob):
    def __init__(self, project):
        AsyncWorkerJob.__init__(self, project)

    def enqueue(self, queue, db):
        db.set_busy(self.project.builddir, ["build_done", "has_changes"])
        logging.info("Enqueueing project for APT update & upgrade")
        AsyncWorkerJob.enqueue(self, queue, db)

    def execute(self, db):
        success = self.build_failed
        try:
            logging.info("APT update started")
            with self.project.buildenv:
                self.project.get_rpcaptcache().update()
            logging.info("APT update finished, upgrade started")
            self.project.get_rpcaptcache().upgrade()
        except Exception:
            logging.exception("APT update & upgrade failed")
        else:
            if read_maxlevel(self.project.builddir) >= logging.ERROR:
                logging.info("APT upgrade finished with Error")
            else:
                logging.info("APT upgrade finished")
                success = self.has_changes
        finally:
            db.reset_busy(self.project.builddir, success)

class APTCommitJob(AsyncWorkerJob):
    def __init__(self, project):
        AsyncWorkerJob.__init__(self, project)

    def enqueue(self, queue, db):
        old_status = db.set_busy(self.project.builddir,
                                 ["build_done", "has_changes"])
        if self.project.get_rpcaptcache().get_changes():
            logging.info("Enqueueing project for package changes")
            AsyncWorkerJob.enqueue(self, queue, db)
        else:
            db.reset_busy(self.project.builddir, old_status)

    def execute(self, db):
        success = self.build_failed
        try:
            logging.info("Applying package changes")
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
        except Exception:
            logging.exception("Applying package changes failed")
        else:
            if read_maxlevel(self.project.builddir) >= logging.ERROR:
                logging.info("Package changes applied with Error")
            else:
                logging.info("Package changes applied successfully")
                succes = self.has_changes
        finally:
            db.reset_busy(self.project.builddir, success)


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

        logging.info("Enqueueing project for generating update package")
        AsyncWorkerJob.enqueue(self, queue, db)

    def execute(self, db):
        upd_filename = self._gen_upd_filename()
        upd_pathname = path.join(self.project.builddir, upd_filename)

        logging.info("Generating update package")

        try:
            gen_update_pkg(self.project, self.base_version_xml, upd_pathname)
            logging.info("Update package generated successfully")
        except Exception:
            logging.exception("Generating update package failed")
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
            logging.info("save version script:")
            do(self.project.savesh_file + ' "%s %s %s"' % (
                self.project.builddir,
                self.project.xml.text("project/version"),
                self.project.xml.text("project/name")),
                allow_fail=True)

        logging.info("Enqueueing project to save package archive")
        AsyncWorkerJob.enqueue(self, queue, db)

    def execute(self, db):
        logging.info("Generating package archive")
        repodir = get_versioned_filename(self.name, self.version,
                                         ".pkgarchive")
        try:
            gen_binpkg_archive(self.project, repodir)
        except Exception:
            logging.exception("Saving version failed")
            db.del_version(self.project.builddir, self.version, force=True)
        else:
            logging.info("Version saved successfully")
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
            logging.warning("Previous project status indicated a failed build\n"
                            "Just checking out the XML file.")

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

        logging.info("Enqueueing project for package archive checkout")
        AsyncWorkerJob.enqueue(self, queue, db)

    def execute(self, db):
        logging.info("Checking out package archive")
        repodir = get_versioned_filename(self.name, self.version,
                                         ".pkgarchive")
        success = self.build_failed
        try:
            checkout_binpkg_archive(self.project, repodir)
            logging.info("Package archive checked out successfully")
        except Exception:
            logging.exception("Checking out package archive failed")
        else:
            success = self.has_changes
        finally:
            db.reset_busy(self.project.builddir, success)


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
                    with elbe_logging({"projects":job.project.builddir}):
                        job.execute(self.db)
            else:
                loop = False
            self.queue.task_done()
