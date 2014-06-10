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

from threading import Thread
from Queue import Queue
from os import path, getcwd, chdir
from contextlib import contextmanager
from urllib import quote
import traceback

from elbepack.dump import dump_fullpkgs
from elbepack.updatepkg import gen_update_pkg

class AsyncWorkerJob(object):
    def __init__ (self, project):
        self.project = project

    def enqueue (self, queue, db):
        queue.put( self )

    def execute (self, db):
        pass


class BuildJob(AsyncWorkerJob):
    def __init__ (self, project):
        AsyncWorkerJob.__init__( self, project )

    def enqueue (self, queue, db):
        db.set_busy( self.project.builddir,
                [ "empty_project", "needs_build", "has_changes",
                  "build_done", "build_failed" ] )
        self.project.log.printo( "Enqueueing project for build" )
        AsyncWorkerJob.enqueue( self, queue, db )

    def execute (self, db):
        try:
            self.project.log.printo( "Build started" )
            self.project.build()
            db.update_project_files( self.project )
            self.project.log.printo( "Build finished successfully" )
            db.reset_busy( self.project.builddir, "build_done" )
        except Exception as e:
            db.update_project_files( self.project )
            self.project.log.printo( "Build failed" )
            self.project.log.printo( traceback.format_exc() )
            db.reset_busy( self.project.builddir, "build_failed" )


class APTUpdateJob(AsyncWorkerJob):
    def __init__ (self, project):
        AsyncWorkerJob.__init__( self, project )

    def enqueue (self, queue, db):
        db.set_busy( self.project.builddir,
                [ "build_done", "has_changes" ] )
        self.project.log.printo( "Enqueueing project for APT cache update" )
        AsyncWorkerJob.enqueue( self, queue, db )

    def execute (self, db):
        try:
            self.project.log.printo( "APT cache update started" )
            with self.project.buildenv:
                self.project.get_rpcaptcache().update()
            self.project.log.printo( "APT cache update finished successfully" )
            db.reset_busy( self.project.builddir,
                    "has_changes" )
        except Exception as e:
            self.project.log.printo( "APT cache update failed" )
            self.project.log.printo( str(e) )
            db.reset_busy( self.project.builddir, "build_failed" )


class APTCommitJob(AsyncWorkerJob):
    def __init__ (self, project):
        AsyncWorkerJob.__init__( self, project )

    def enqueue (self, queue, db):
        old_status = db.set_busy( self.project.builddir,
                [ "build_done", "has_changes" ] )
        if self.project.get_rpcaptcache().get_changes():
            self.project.log.printo( "Enqueueing project for package changes" )
            AsyncWorkerJob.enqueue( self, queue, db )
        else:
            db.reset_busy( self.project.builddir, old_status )

    def execute (self, db):
        try:
            self.project.log.printo( "Applying package changes" )
            with self.project.buildenv:
                # Commit changes, update full package list and write
                # out new source.xml
                self.project.get_rpcaptcache().commit()
                dump_fullpkgs( self.project.xml,
                        self.project.buildenv.rfs,
                        self.project.get_rpcaptcache() )

            sourcexmlpath = path.join( self.project.builddir,
                    "source.xml" )
            self.project.xml.xml.write( sourcexmlpath )

            self.project.log.printo( "Package changes applied successfully" )
            db.reset_busy( self.project.builddir,
                    "has_changes" )
        except Exception as e:
            self.project.log.printo( "Applying package changes failed" )
            self.project.log.printo( str(e) )
            db.reset_busy( self.project.builddir,
                    "build_failed" )


class GenUpdateJob(AsyncWorkerJob):
    def __init__ (self, project, base_version):
        self.name = project.xml.text( "/project/name" )
        self.base_version = base_version
        self.current_version = project.xml.text( "/project/version" )
        AsyncWorkerJob.__init__(self, project)

    def enqueue (self, queue, db):
        self.old_status = db.set_busy( self.project.builddir,
                [ "build_done", "has_changes" ] )
        self.base_version_xml = db.get_version_xml( self.project.builddir,
                self.base_version )

        self.project.log.printo(
                "Enqueueing project for generating update package" )

        AsyncWorkerJob.enqueue( self, queue, db )

    def execute (self, db):
        upd_filename = self._gen_upd_filename()
        upd_pathname = path.join( self.project.builddir, upd_filename )

        self.project.log.printo( "Generating update package" )

        try:
            gen_update_pkg( self.project, self.base_version_xml, upd_pathname )
            self.project.log.printo( "Update package generated successfully" )
        except Exception as e:
            self.project.log.printo( "Generating update package failed" )
            self.project.log.printo( str(e) )
        finally:
            # Update generation does not change the project, so we always
            # keep the old status
            db.add_project_file( self.project.builddir, upd_filename,
                    "application/octet-stream",
                    "Update package from %s to %s" %
                    ( self.base_version, self.current_version ) )
            db.reset_busy( self.project.builddir, self.old_status )

    def _gen_upd_filename (self):
        filename = quote( self.name, ' ' ) + '_'
        filename += quote( self.base_version ) + '_'
        filename += quote( self.current_version ) + '.upd'

        return filename


class SaveVersionJob(AsyncWorkerJob):
    def __init__ (self, project, description):
        AsyncWorkerJob.__init__( self, project )
        self.description = description

    def enqueue (self, queue, db):
        self.old_status = db.set_busy( self.project.builddir,
                [ "build_done", "has_changes" ] )
        self.project.log.printo( "Enqueueing project to save version" )
        AsyncWorkerJob.enqueue( self, queue, db )

    def execute (self, db):
        self.project.log.printo( "Saving version" )
        try:
            # TODO: Generate APT repository with all packages installed and
            # store it somewhere
            db.save_version( self.project.builddir, self.description )
            self.project.log.printo( "Version saved successfully" )
        except Exception as e:
            self.project.log.printo( "Saving version failed" )
            self.project.log.printo( str(e) )
        finally:
            db.reset_busy( self.project.builddir, self.old_status )


@contextmanager
def savecwd ():
    oldcwd = getcwd()
    try:
        yield
    finally:
        chdir( oldcwd )


class AsyncWorker(Thread):
    def __init__ (self, db):
        Thread.__init__( self )
        self.db = db
        self.queue = Queue()
        self.start()

    def enqueue (self, job):
        job.enqueue( self.queue, self.db )

    def run (self):
        while True:
            with savecwd():
                job = self.queue.get()
                job.execute( self.db )
