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

class AsyncBuilder(Thread):
    def __init__ (self, db):
        Thread.__init__( self )
        self.db = db
        self.queue = Queue()
        self.start()

    def enqueue (self, ep):
        self.db.set_build_in_progress( ep.builddir )
        self.queue.put( ep )

    def run (self):
        while True:
            ep = self.queue.get()

            try:
                ep.build()
                self.db.set_build_done( ep.builddir, successful=True )
            except Exception as e:
                self.db.set_build_done( ep.builddir, successful=False )
                print e     # XXX Think about better error handling here
