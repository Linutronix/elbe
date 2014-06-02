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
        db.set_busy( self.project.builddir, True )
        AsyncWorkerJob.enqueue( self, queue, db )

    def execute (self, db):
        try:
            self.project.build()
            db.update_project_files( self.project )
            db.reset_busy( self.project.builddir, "build_done" )
        except Exception as e:
            db.update_project_files( self.project )
            db.reset_busy( self.project.builddir, "build_failed" )
            print e     # TODO: Think about better error handling here


class APTUpdateJob(AsyncWorkerJob):
    def __init__ (self, project):
        AsyncWorkerJob.__init__( self, project )

    def enqueue (self, queue, db):
        db.set_busy( self.project.builddir, False )
        AsyncWorkerJob.enqueue( self, queue, db )

    def execute (self, db):
        try:
            with self.project.buildenv:
                self.project.get_rpcaptcache().update()
                db.reset_busy( self.project.builddir,
                        "has_changes" )
        except Exception as e:
            db.reset_busy( self.project.builddir, "build_failed" )
            print e     # TODO: Think about better error handling here


class APTCommitJob(AsyncWorkerJob):
    def __init__ (self, project):
        AsyncWorkerJob.__init__( self, project )

    def enqueue (self, queue, db):
        old_status = db.set_busy( self.project.builddir, False )
        if self.project.get_rpcaptcache().get_changes():
            AsyncWorkerJob.enqueue( self, queue, db )
        else:
            db.reset_busy( self.project.builddir, old_status )

    def execute (self, db):
        try:
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

                db.reset_busy( self.project.builddir,
                        "has_changes" )
        except Exception as e:
            db.reset_busy( self.project.builddir,
                    "build_failed" )
            print e     # TODO: Think about better error handling here


class GenUpdateJob(AsyncWorkerJob):
    def __init__ (self, project, base_version):
        self.name = project.xml.text( "/project/name" )
        self.base_version = base_version
        self.current_version = project.xml.text( "/project/version" )
        AsyncWorkerJob.__init__(self, project)

    def enqueue (self, queue, db):
        self.old_status = db.set_busy( self.project.builddir, False )
        self.base_version_xml = db.get_version_xml( self.project.builddir,
                self.base_version )
        AsyncWorkerJob.enqueue( self, queue, db )

    def execute (self, db):
        try:
            gen_update_pkg( self.project, self.base_version_xml,
                    self._gen_upd_pathname() )
        except Exception as e:
            print e     # TODO: Think about better error handling here
        finally:
            # Update generation does not change the project, so we always
            # keep the old status
            # TODO: Add resulting update file to the project file table
            db.reset_busy( self.project.builddir, self.old_status )

    def _gen_upd_pathname (self):
        filename = quote( self.name, ' ' ) + '_'
        filename += quote( self.base_version ) + '_'
        filename += quote( self.current_version ) + '.upd'

        pathname = path.join( self.project.builddir, filename )
        return pathname


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
