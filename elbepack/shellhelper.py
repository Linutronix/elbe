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

class CommandError(Exception):
    def __init__(self, cmd, returncode):
        Exception.__init__(self)
        self.returncode = returncode
        self.cmd = cmd

    def __repr__(self):
        return "Error: %d returned from Command %s" % (
                                             self.returncode, self.cmd)

def system(cmd, allow_fail=False):
    ret = os.system(cmd)

    if ret != 0:
        if not allow_fail:
            raise CommandError(cmd, p.returncode)


def command_out(cmd, input=None):
    if input is None:
        p = Popen(cmd, shell=True, stdout=PIPE, stderr=STDOUT )
        output, stderr = p.communicate()
    else:
        p = Popen(cmd, shell=True, stdout=PIPE, stderr=STDOUT, stdin=PIPE)
        output, stderr = p.communicate(input=input)

    return p.returncode, output

def command_out_stderr(cmd, input=None):
    if input is None:
        p = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE )
        output, stderr = p.communicate()
    else:
        p = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE, stdin=PIPE)
        output, stderr = p.communicate(input=input)

    return p.returncode, output, stderr

