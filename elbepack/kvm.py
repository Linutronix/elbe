# ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (C) 2016  Linutronix GmbH
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

class NoExecutableFound (Exception):
    def __init__ (self, exe_fname):
        Exception.__init__ (self, 'No Executable for "%s" found')

kvm_exe_list = [
    '/usr/bin/kvm',
    '/usr/bin/qemu-kvm',
    '/usr/libexec/qemu-kvm'
    ]

def find_kvm_exe ():
    for fname in kvm_exe_list:
        if os.path.isfile(fname) and os.access(fname, os.X_OK):
            return fname

    return 'kvm_executable_not_found'
