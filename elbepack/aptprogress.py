# ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (C) 2013  Linutronix GmbH
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

from apt.progress.base import InstallProgress, AcquireProgress
from apt_pkg import size_to_str
import os

class ElbeInstallProgress (InstallProgress):

    def __init__ (self, cb=None):
        InstallProgress.__init__ (self)
        self.cb = cb

    def write (self, line):
        line = str (self.percent) + "% " + line
        if self.cb:
            self.cb (line)
        else:
            print line

    def processing (self, pkg, stage):
        InstallProgress.processing (self, pkg, stage)
        self.write ("processing: " + pkg + " - " + stage)

    def dpkg_status_change (self, pkg, status):
        InstallProgress.dpkg_status_change (self, pkg, status)
        self.write (status)

    def status_change (self, pkg, percent, status):
        InstallProgress.status_change (self, pkg, percent, status)
        self.write (status)

    def fork(self):
        retval = os.fork()
        if (retval):
            self.child_pid = retval
        return retval

    def finishUpdate(self):
        self.write ("update finished")

class ElbeAcquireProgress (AcquireProgress):

    def __init__ (self, cb=None):
        AcquireProgress.__init__ (self)
        self._id = long(1)
        self.cb = cb

    def write (self, line):
        if self.cb:
            self.cb (line)
        else:
            print line

    def ims_hit(self, item):
        line = 'Hit ' + item.description
        if item.owner.filesize:
            line += ' [%sB]' % size_to_str(item.owner.filesize)
        self.write (line)

    def fail(self, item):
        if item.owner.status == item.owner.STAT_DONE:
            self.write ("Ign " + item.description)

    def fetch(self, item):
        if item.owner.complete:
            return
        item.owner.id = self._id
        self._id += 1
        line = "Get:" + str (item.owner.id) + " " + item.description
        if item.owner.filesize:
            line += (" [%sB]" % size_to_str(item.owner.filesize))

        self.write(line)

    def pulse (self, owner):
        return True
