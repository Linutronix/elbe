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

class AsyncWorkerJob(object):
    BUILD, APT_COMMIT = range(2)

    def __init__ (self, project, action):
        self.project = project
        self.action = action

class AsyncWorker(Thread):
    def __init__ (self, db):
        Thread.__init__( self )
        self.db = db
        self.queue = Queue()
        self.start()

    def enqueue (self, job):
        if job.action == AsyncWorkerJob.BUILD:
            self.db.set_busy( job.project.builddir, True )
            self.queue.put( job )

        elif job.action == AsyncWorkerJob.APT_COMMIT:
            old_status = self.db.set_busy( job.project.builddir, False )
            if job.project.get_rpcaptcache().get_changes():
                self.queue.put( job )
            else:
                self.db.reset_busy( job.project.builddir, old_status )

    def run (self):
        while True:
            job = self.queue.get()

            if job.action == AsyncWorkerJob.BUILD:
                try:
                    job.project.build()
                    self.db.reset_busy( job.project.builddir,
                            "build_done" )
                except Exception as e:
                    self.db.reset_busy( job.project.builddir,
                            "build_failed" )
                    print e     # TODO: Think about better error handling here

            elif job.action == AsyncWorkerJob.APT_COMMIT:
                try:
                    with job.project.buildenv:
                        job.project.get_rpcaptcache().commit()
                        self.db.reset_busy( job.project.builddir,
                                "has_changes" )
                except Exception as e:
                    self.db.reset_busy( job.project.builddir,
                            "build_failed" )
                    print e     # TODO: Think about better error handling here
