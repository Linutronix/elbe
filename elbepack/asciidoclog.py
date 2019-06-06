# ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (c) 2014, 2016 Torben Hohn <torben.hohn@linutronix.de>
# Copyright (c) 2014 Ferdinand Schwenk <ferdinand.schwenk@emtrion.de>
# Copyright (c) 2014, 2016-2017 Manuel Traut <manut@linutronix.de>
#
# SPDX-License-Identifier: GPL-3.0-or-later

import os
import sys
import logging

from elbepack.shellhelper import get_command_out, do, chroot, CommandError

class LogBase(object):
    def __init__(self, *args, **kwargs):
        pass

    def printo(self, text=""):
        logging.info(text)

    def print_raw(self, text):
        self.printo(text)

    def h1(self, text):
        self.printo(text)

    def h2(self, text):
        self.printo(text)

    def table(self):
        pass

    def verbatim_start(self):
        pass

    def verbatim_end(self):
        pass

    def do(self, cmd, **kwargs):
        return do(cmd, **kwargs)

    def chroot(self, directory, cmd, **kwargs):
        return chroot(directory, cmd, **kwargs)

    def get_command_out(self, cmd, **kwargs):
        return get_command_out(cmd, **kwargs)

class ASCIIDocLog (LogBase):
    pass

class StdoutLog(LogBase):
    pass

class StderrLog(LogBase):
    pass
