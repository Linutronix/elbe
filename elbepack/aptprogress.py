# ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (c) 2014 Torben Hohn <torbenh@linutronix.de>
# Copyright (c) 2014-2017 Manuel Traut <manut@linutronix.de>
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import print_function

import os

from apt.progress.base import InstallProgress, AcquireProgress, OpProgress
from apt_pkg import size_to_str


class ElbeInstallProgress (InstallProgress):

    def __init__(self, cb=None, fileno=2):
        InstallProgress.__init__(self)
        self.cb = cb
        self.fileno = fileno

    def write(self, line):
        if line == 'update finished':
            # This is class attribute inherited by InstallProgress.
            # Pylint is confused by this but the attribute does exists
            # on this type!
            #
            # pylint: disable=attribute-defined-outside-init
            self.percent = 100

        line = str(self.percent) + "% " + line
        line.replace('\f', '')
        if self.cb:
            self.cb(line)
        else:
            print(line)

    def processing(self, pkg, stage):
        self.write("processing: " + pkg + " - " + stage)

    def dpkg_status_change(self, pkg, status):
        self.write(pkg + " - " + status)

    def status_change(self, pkg, percent, status):
        self.write(pkg + " - " + status + " " + str(percent) + "%")

    def run(self, obj):
        try:
            obj.do_install(self.fileno)
        except AttributeError:
            print("installing .deb files is not supported by elbe progress")
            raise SystemError
        return 0

    def fork(self):
        retval = os.fork()
        if retval:
            # This is class attribute inherited by InstallProgress.
            # Pylint is confused by this but the attribute does exists
            # on this type!
            #
            # pylint: disable=attribute-defined-outside-init
            self.child_pid = retval
        return retval

    def finishUpdate(self):
        self.write("update finished")


class ElbeAcquireProgress (AcquireProgress):

    def __init__(self, cb=None):
        AcquireProgress.__init__(self)
        self._id = 1
        self.cb = cb

    def write(self, line):
        line.replace('\f', '')
        if self.cb:
            self.cb(line)
        else:
            print(line)

    def ims_hit(self, item):
        line = 'Hit ' + item.description
        if item.owner.filesize:
            line += ' [%sB]' % size_to_str(item.owner.filesize)
        self.write(line)

    def fail(self, item):
        if item.owner.status == item.owner.STAT_DONE:
            self.write("Ign " + item.description)

    def fetch(self, item):
        if item.owner.complete:
            return
        item.owner.id = self._id
        self._id += 1
        line = "Get:" + str(item.owner.id) + " " + item.description
        if item.owner.filesize:
            line += (" [%sB]" % size_to_str(item.owner.filesize))

        self.write(line)

    @staticmethod
    def pulse(_owner):
        return True


class ElbeOpProgress (OpProgress):

    def __init__(self, cb=None):
        OpProgress.__init__(self)
        self._id = 1
        self.cb = cb

    def write(self, line):
        line.replace('\f', '')
        if self.cb:
            self.cb(line)
        else:
            print(line)

    def update(self, percent=None):
        pass

    def done(self):
        pass
