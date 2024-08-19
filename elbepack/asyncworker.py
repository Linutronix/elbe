# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2014-2018 Linutronix GmbH

import logging
import multiprocessing
from contextlib import contextmanager
from os import chdir, getcwd

from elbepack.elbeproject import AptCacheCommitError, AptCacheUpdateError
from elbepack.log import elbe_logging, read_maxlevel, reset_level
from elbepack.rfs import DebootstrapException


class AsyncWorkerJob:

    build_done = 'build_done'
    build_failed = 'build_failed'
    has_changes = 'has_changes'

    def __init__(self, project):
        self.project = project

    def enqueue(self, queue, _db):
        reset_level(self.project.builddir)
        queue.put(self)

    def execute(self, _db):
        pass


class BuildSysrootJob(AsyncWorkerJob):

    def enqueue(self, queue, db):
        db.set_busy(self.project.builddir,
                    ['empty_project', 'needs_build', 'has_changes',
                     'build_done', 'build_failed'])
        logging.info('Enqueueing project for building sysroot')
        super().enqueue(queue, db)

    def execute(self, db):
        success = self.build_failed
        try:
            logging.info('Build sysroot started')
            self.project.build_sysroot()
            db.update_project_files(self.project)
        except Exception:
            logging.exception('Build sysroot failed')
        else:
            if read_maxlevel(self.project.builddir) >= logging.ERROR:
                logging.info('Build finished with Error')
            else:
                logging.info('Build finished successfully')
                success = self.build_done
        finally:
            db.update_project_files(self.project)
            db.reset_busy(self.project.builddir, success)


class BuildSDKJob(AsyncWorkerJob):

    def enqueue(self, queue, db):
        db.set_busy(self.project.builddir,
                    ['empty_project', 'needs_build', 'has_changes',
                     'build_done', 'build_failed'])
        logging.info('Enqueueing project for building SDK')
        super().enqueue(queue, db)

    def execute(self, db):
        success = self.build_failed
        try:
            logging.info('Build SDK started')
            self.project.build_sdk()
        except Exception:
            logging.exception('Build SDK Failed')
        else:
            if read_maxlevel(self.project.builddir) >= logging.ERROR:
                logging.info('Build finished with Error')
            else:
                logging.info('Build finished successfully')
                success = self.build_done
        finally:
            db.update_project_files(self.project)
            db.reset_busy(self.project.builddir, success)


class BuildCDROMsJob(AsyncWorkerJob):
    def __init__(self, project, build_bin, build_src):
        super().__init__(project)
        self.build_bin = build_bin
        self.build_src = build_src

    def enqueue(self, queue, db):
        db.set_busy(self.project.builddir,
                    ['empty_project', 'needs_build', 'has_changes',
                     'build_done', 'build_failed'])
        logging.info('Enqueueing project for building CDROMs')
        super().enqueue(queue, db)

    def execute(self, db):
        success = self.build_failed
        try:
            logging.info('Build CDROMs started')
            self.project.build_cdroms(self.build_bin, self.build_src)
        except Exception:
            logging.exception('Build CDROMs failed')
        else:
            if read_maxlevel(self.project.builddir) >= logging.ERROR:
                logging.info('Build finished with Error')
            else:
                logging.info('Build finished successfully')
                success = self.build_done
        finally:
            db.update_project_files(self.project)
            db.reset_busy(self.project.builddir, success)


class BuildChrootTarJob(AsyncWorkerJob):

    def enqueue(self, queue, db):
        db.set_busy(self.project.builddir,
                    ['empty_project', 'needs_build', 'has_changes',
                     'build_done', 'build_failed'])
        logging.info('Enqueueing project for building croot tar')
        super().enqueue(queue, db)

    def execute(self, db):
        success = self.build_failed
        try:
            logging.info('Build chroot tarball started')
            self.project.build_chroottarball()
        except Exception:
            logging.exception('Build chrroot tarball failed')
        else:
            if read_maxlevel(self.project.builddir) >= logging.ERROR:
                logging.info('Build finished with Error')
            else:
                logging.info('Build finished successfully')
                success = self.build_done
        finally:
            db.update_project_files(self.project)
            db.reset_busy(self.project.builddir, success)


class BuildJob(AsyncWorkerJob):
    def __init__(self, project, build_bin, build_src, skip_pbuilder):
        super().__init__(project)
        self.build_bin = build_bin
        self.build_src = build_src
        self.skip_pbuilder = skip_pbuilder

    def enqueue(self, queue, db):
        db.set_busy(self.project.builddir,
                    ['empty_project', 'needs_build', 'has_changes',
                     'build_done', 'build_failed'])
        logging.info('Enqueueing project for build')
        super().enqueue(queue, db)

    def execute(self, db):

        success = self.build_failed
        try:
            logging.info('Build started')
            self.project.build(skip_pkglist=False,
                               build_bin=self.build_bin,
                               build_sources=self.build_src,
                               skip_pbuild=self.skip_pbuilder)
        except (DebootstrapException, AptCacheCommitError, AptCacheUpdateError) as e:
            if isinstance(e, DebootstrapException):
                err = 'Debootstrap failed to install the base rootfilesystem.'
            elif isinstance(e, AptCacheCommitError):
                err = 'Failed to commit the AptCache changes.'
            elif isinstance(e, AptCacheUpdateError):
                err = 'Failed to build the Apt Cache.'

            logging.exception('%s\n'
                              'Probable cause might be:\n'
                              '  - Problems with internet connection\n'
                              '  - Broken mirrors\n', err)
        except Exception:
            logging.exception('Build failed')
        else:
            if read_maxlevel(self.project.builddir) >= logging.ERROR:
                logging.info('Build finished with Error')
            else:
                logging.info('Build finished successfully')
                success = self.build_done
        finally:
            db.update_project_files(self.project)
            db.reset_busy(self.project.builddir, success)


class PdebuildJob(AsyncWorkerJob):
    def __init__(self, project, profile='', cross=False):
        super().__init__(project)
        self.profile = profile
        self.cross = cross

    def enqueue(self, queue, db):
        db.set_busy(self.project.builddir,
                    ['empty_project', 'needs_build', 'has_changes',
                     'build_done', 'build_failed'])
        logging.info('Enqueueing project for pdebuild')
        super().enqueue(queue, db)

    def execute(self, db):
        success = self.build_failed
        try:
            logging.info('Pdebuild started')
            self.project.pdebuild(self.profile, self.cross)
        except Exception:
            logging.exception('Pdebuild failed')
        else:
            if read_maxlevel(self.project.builddir) >= logging.ERROR:
                logging.info('Pdeb finished with Error')
            else:
                logging.info('Pdeb finished successfully')
                success = self.build_done
        finally:
            db.update_project_files(self.project)
            db.reset_busy(self.project.builddir, success)


class CreatePbuilderJob(AsyncWorkerJob):
    def __init__(self, project, ccachesize, cross=False, noccache=False):
        super().__init__(project)
        self.cross = cross
        self.noccache = noccache
        self.ccachesize = ccachesize

    def enqueue(self, queue, db):
        db.set_busy(self.project.builddir,
                    ['empty_project', 'needs_build', 'has_changes',
                     'build_done', 'build_failed'])
        logging.info('Enqueueing project to have the pbuilder built')
        super().enqueue(queue, db)

    def execute(self, db):
        success = self.build_failed
        try:
            logging.info('Building pbuilder started')
            self.project.create_pbuilder(self.cross, self.noccache,
                                         self.ccachesize)
        except Exception:
            logging.exception('Pbuilder failed')
        else:
            logging.info('Pbuilder finished successfully')
            success = self.build_done
        finally:
            db.update_project_files(self.project)
            db.reset_busy(self.project.builddir, success)


class UpdatePbuilderJob(AsyncWorkerJob):

    def enqueue(self, queue, db):
        db.set_busy(self.project.builddir,
                    ['empty_project', 'needs_build', 'has_changes',
                     'build_done', 'build_failed'])
        logging.info('Enqueueing project to update the pbuilder')
        super().enqueue(queue, db)

    def execute(self, db):
        success = self.build_done
        try:
            logging.info('Updating pbuilder started')
            self.project.update_pbuilder()
        except Exception:
            db.update_project_files(self.project)
            logging.exception('update Pbuilder failed')
        else:
            if read_maxlevel(self.project.builddir) >= logging.ERROR:
                logging.info('Updating Pbuilder finished with Error')
            else:
                logging.info('Updating Pbuilder finished successfully')
                success = self.build_done
        finally:
            db.reset_busy(self.project.builddir, success)


@contextmanager
def savecwd():
    oldcwd = getcwd()
    try:
        yield
    finally:
        chdir(oldcwd)


class AsyncWorker(multiprocessing.Process):
    def __init__(self, db):
        super().__init__(name='AsyncWorker')
        self.db = db
        self.queue = multiprocessing.JoinableQueue()
        self.start()

    def stop(self):
        self.queue.put(None)
        self.queue.join()
        self.join()

    def enqueue(self, job):
        job.enqueue(self.queue, self.db)

    def run(self):
        while True:
            job = self.queue.get()
            if job is None:
                break

            with savecwd():
                with elbe_logging(projects=job.project.builddir):
                    job.execute(self.db)
            self.queue.task_done()
