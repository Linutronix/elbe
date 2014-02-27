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
from subprocess import Popen, PIPE, STDOUT

class commanderror(Exception):
    def __init__(self, cmd, returncode):
        self.returncode = returncode
        self.cmd = cmd

    def __repr__(self):
        return "Error: %d returned from Command %s" % (
                                             self.returncode, self.cmd)

class ASCIIDocLog (object):
    def __init__(self, fname):
        if os.path.isfile(fname):
            os.unlink(fname)
        self.fp = file(fname, "w")

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

    def do(self, cmd, **args):

        if args.has_key("allow_fail"):
            allow_fail = args["allow_fail"]
        else:
            allow_fail = False

        self.printo( "running cmd +%s+" % cmd )
        self.verbatim_start()
        p = Popen(cmd, shell=True, stdout=PIPE, stderr=STDOUT )
        output, stderr = p.communicate()
        self.print_raw( output )
        self.verbatim_end()

        if p.returncode != 0:
            self.printo( "Command failed with errorcode %d" % p.returncode )
            if not allow_fail:
                raise commanderror(cmd, p.returncode)

    def chroot(self, directory, cmd, **args):
        chcmd = "chroot %s %s" % (directory, cmd)
        self.do( chcmd, **args )

    def get_command_out(self, cmd, **args):

        if args.has_key("allow_fail"):
            allow_fail = args["allow_fail"]
        else:
            allow_fail = False

        self.printo( "getting output from cmd +%s+" % cmd )
        self.verbatim_start()
        p = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE )
        output, stderr = p.communicate()
        self.print_raw( stderr )
        self.verbatim_end()


        if p.returncode != 0:
            self.printo( "Command failed with errorcode %d" % p.returncode )
            if not allow_fail:
                raise commanderror(cmd, p.returncode)

        return output
