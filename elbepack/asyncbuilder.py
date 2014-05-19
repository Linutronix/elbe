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

class BuildJob(object):
    FULL, APT_COMMIT = range(2)

    def __init__ (self, project, buildtype):
        self.project = project
        self.buildtype = buildtype

class AsyncBuilder(Thread):
    def __init__ (self, db):
        Thread.__init__( self )
        self.db = db
        self.queue = Queue()
        self.start()

    def enqueue (self, buildjob):
        if buildjob.buildtype == BuildJob.FULL:
            self.db.set_build_in_progress( buildjob.project.builddir )
            self.queue.put( buildjob )
        elif buildjob.buildtype == BuildJob.APT_COMMIT:
            self.db.set_build_in_progress( buildjob.project.builddir )
            if buildjob.project.get_rpcaptcache().get_changes():
                self.queue.put( buildjob )
            else:
                self.db.set_build_done( buildjob.project.builddir )

    def run (self):
        while True:
            job = self.queue.get()

            try:
                if job.buildtype == BuildJob.FULL:
                    job.project.build()
                elif job.buildtype == BuildJob.APT_COMMIT:
                    with job.project.buildenv:
                        job.project.get_rpcaptcache().commit()

                self.db.set_build_done( job.project.builddir, successful=True )
            except Exception as e:
                self.db.set_build_done( job.project.builddir, successful=False )
                print e     # XXX Think about better error handling here
