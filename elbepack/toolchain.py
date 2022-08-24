# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2014, 2017 Linutronix GmbH

import string

import glob
import os

arch2triple = {"armhf": "arm-linux-gnueabihf", "armel": "arm-linux-gnueabi"}

class Toolchain:
    libc_path = "${triple}/libc"
    gcc_libpath = "${triple}/lib"
    pkg_libs = {}

    def __init__(self, path, arch, triple=None):
        self.path = path
        self.arch = arch
        if triple:
            self.triple = triple
        else:
            self.triple = arch2triple[arch]

    def get_fullpath(self, path):
        replace = {"triple": self.triple}
        tpl = string.Template(path)
        p = tpl.substitute(replace)

        return os.path.join(self.path, p)

    def get_files_for_pkg(self, pkgname):
        globs = self.pkg_libs[pkgname]

        files = []
        for g in globs:
            gg = os.path.join(self.get_fullpath(self.gcc_libpath), g)
            files += glob.glob(gg)

        return files


class LinaroToolchain(Toolchain):
    pkg_libs = {"libasan0": ["libasan.so.*"],
                "libatomic1": ["libatomic.so.*"],
                "libgcc1": ["libgcc_s.so.*"],
                "libgfortran3": ["libgfortran.so.*"],
                "libgomp1": ["libgomp.so.*"],
                "libmudflap0": ["libmudflap.so.*", "libmudflapth.so.*"],
                "libssp0": ["libssp.so.*"],
                "libstdc++6": ["libstdc++.so.*"]}

    pkg_deps = {
        "libasan0": "libc6 (>= 2.13-28), "
                    "libstdc++ (>= 4.8.3), "
                    "libgcc1 (>= 4.8.3)",
        "libatomic1": "libc6 (>= 2.13-28)",
        "libgcc1": "libc6 (>= 2.13-28)",
        "libgfortran3": "libgcc1 (>= 4.8.3)",
        "libgomp1": "libc6 (>= 2.13-28)",
        "libmudflap0": "libc6 (>= 2.13-28)",
        "libssp0": "libc6 (>= 2.13-28)",
        "libstdc++6": "libc6 (>= 2.13-28), libgcc1 (>= 4.8.3)"}


class LinaroToolchainArmel(LinaroToolchain):
    gcc_libpath = "arm-linux-gnueabihf/lib/arm-linux-gnueabi"


def get_toolchain(typ, path, arch):
    if typ == "linaro":
        return LinaroToolchain(path, arch)
    if typ == "linaro_armel":
        return LinaroToolchainArmel(path, arch)

    raise Exception
