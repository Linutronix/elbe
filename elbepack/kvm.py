# ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (c) 2016 Torben Hohn <torben.hohn@linutronix.de>
# Copyright (c) 2017 Kurt Kanzenbach <kurt@linutronix.de>
# Copyright (c) 2017 Manuel Traut <manut@linutronix.de>
#
# SPDX-License-Identifier: GPL-3.0-or-later

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
