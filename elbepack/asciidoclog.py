#!/usr/bin/env python
#
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

import os
import sys

from elbepack.shellhelper import CommandError, command_out_stderr, command_out

class LogBase(object):
    def __init__(self, fp):
        self.fp = fp

    def printo(self, text=""):
        self.fp.write(text+"\n")

    def print_raw(self, text):
        self.fp.write(text)

    def h1(self, text):
        self.printo()
        self.printo(text)
        self.printo("="*len(text))
        self.printo()

    def h2(self, text):
        self.printo()
        self.printo(text)
        self.printo("-"*len(text))
        self.printo()

    def table(self):
        self.printo( "|=====================================" )

    def verbatim_start(self):
        self.printo( "------------------------------------------------------------------------------" )

    def verbatim_end(self):
        self.printo( "------------------------------------------------------------------------------" )
        self.printo()

    def do(self, cmd, allow_fail=False, input=None):

        if input == None:
            self.printo( "running cmd +%s+" % cmd )
        else:
            self.printo( "running cmd +%s with STDIN %s+" % (cmd, input) )

        ret, output = command_out(cmd, input=input)

        if len(output) != 0:
            self.verbatim_start()
            self.print_raw( output )
            self.verbatim_end()

        if ret != 0:
            self.printo( "Command failed with errorcode %d" % ret )
            if not allow_fail:
                raise CommandError(cmd, ret)

    def chroot(self, directory, cmd, **args):
        os.environ["LANG"] = "C"
        os.environ["LANGUAGE"] = "C"
        os.environ["LC_ALL"] = "C"

        chcmd = "chroot %s %s" % (directory, cmd)
        self.do( chcmd, **args )

    def get_command_out(self, cmd, allow_fail=False):

        self.printo( "getting output from cmd +%s+" % cmd )

        ret, output, stderr = command_out_stderr(cmd)

        if len(stderr) != 0:
            self.verbatim_start()
            self.print_raw( stderr )
            self.verbatim_end()

        if ret != 0:
            self.printo( "Command failed with errorcode %d" % ret )
            if not allow_fail:
                raise CommandError(cmd, ret)

        return output

class ASCIIDocLog (LogBase):
    def __init__(self, fname):
        if os.path.isfile(fname):
            os.unlink(fname)
        fp = file(fname, "w", 1)

        LogBase.__init__(self, fp)

class StdoutLog(LogBase):
    def __init__(self):
        LogBase.__init__(self, sys.stdout)

class StderrLog(LogBase):
    def __init__(self):
        LogBase.__init__(self, sys.stderr)
