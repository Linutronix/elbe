# ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (c) 2016 Torben Hohn <torben.hohn@linutronix.de>
# Copyright (c) 2017 Kurt Kanzenbach <kurt@linutronix.de>
# Copyright (c) 2017 Manuel Traut <manut@linutronix.de>
#
# SPDX-License-Identifier: GPL-3.0-or-later

import os

from elbepack.shellhelper import command_out

kvm_exe_list = [
    '/usr/bin/kvm',
    '/usr/bin/qemu-kvm',
    '/usr/libexec/qemu-kvm',
    '/usr/bin/qemu-system-x86_64'
]

cached_kvm_infos = None

def find_kvm_exe():

    # pylint: disable=global-statement
    global cached_kvm_infos

    if cached_kvm_infos:
        return cached_kvm_infos

    version = "0.0.0"
    args = []

    for fname in kvm_exe_list:

        if os.path.isfile(fname) and os.access(fname, os.X_OK):
            # determine kvm version
            _, stdout = command_out(fname + ' --version')
            for line in stdout.splitlines():
                if "version" in line:
                    version = line.split()[3].split('(')[0].strip()

            if fname == "/usr/bin/qemu-system-x86_64":
                args.append("-enable-kvm")

            cached_kvm_infos = {
                "exec_name": fname,
                "version": version,
                "args":args
            }

            return cached_kvm_infos

    return {
        "exec_name": "kvm_executable_not_found",
        "version": version,
        "args": args
    }
