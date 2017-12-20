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
import subprocess

kvm_exe_list = [
    '/usr/bin/kvm',
    '/usr/bin/qemu-kvm',
    '/usr/libexec/qemu-kvm',
    '/usr/bin/qemu-system-x86_64'
]


def find_kvm_exe():
    for fname in kvm_exe_list:
        if os.path.isfile(fname) and os.access(fname, os.X_OK):
            # determine kvm version
            cmd = subprocess.Popen(
                fname + ' --version',
                shell=True,
                stdout=subprocess.PIPE)
            for line in cmd.stdout:
                if "version" in line:
                    version = line.split()[3].split('(')[0].strip()

            if fname == "/usr/bin/qemu-system-x86_64":
                fname += " -enable-kvm"

            return fname, version

    return 'kvm_executable_not_found'
