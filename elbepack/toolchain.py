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

import string
import glob
import os

arch2triple = { "armhf": "arm-linux-gnueabihf", "armel": "arm-linux-gnueabi" }

class Toolchain(object):
    def __init__( self, path, arch, triple=None ):
        self.path = path
        self.arch = arch
        if triple:
            self.triple = triple
        else:
            self.triple = arch2triple[arch]


    def get_fullpath( self, path ):
        replace = {"triple": self.triple}
        tpl = string.Template(path)
        p = tpl.substitute( replace )

        return os.path.join( self.path, p )


    def get_files_for_pkg( self, pkgname ):
        globs = self.pkg_libs[pkgname]

        files = []
        for g in globs:
            gg = os.path.join( self.get_fullpath( self.gcc_libpath ), g )
            files += glob.glob( gg )

        return files

    

class LinaroToolchain(Toolchain):
    libc_path = "${triple}/libc"
    gcc_libpath = "${triple}/lib"
    pkg_libs = { "libasan0": ["libasan.so.*"],
                 "libatomic1": ["libatomic.so.*"],
                 "libgcc1": ["libgcc_s.so.*"],
                 "libgfortran3": ["libgfortran.so.*"],
                 "libgomp1": ["libgomp.so.*"],
                 "libmudflap0": ["libmudflap.so.*", "libmudflapth.so.*"],
                 "libssp0": ["libssp.so.*"],
                 "libstdc++6": ["libstdc++.so.*"] }

    pkg_deps = { "libasan0": "libc6 (>= 2.13-28), libstdc++ (>= 4.8.3), libgcc1 (>= 4.8.3)",
                 "libatomic1": "libc6 (>= 2.13-28)",
                 "libgcc1": "libc6 (>= 2.13-28)",
                 "libgfortran3": "libgcc1 (>= 4.8.3)",
                 "libgomp1": "libc6 (>= 2.13-28)",
                 "libmudflap0": "libc6 (>= 2.13-28)",
                 "libssp0": "libc6 (>= 2.13-28)",
                 "libstdc++6": "libc6 (>= 2.13-28), libgcc1 (>= 4.8.3)" }

class LinaroToolchainArmel(LinaroToolchain):
    gcc_libpath = "arm-linux-gnueabihf/lib/arm-linux-gnueabi"


def get_toolchain( typ, path, arch ):
    if typ=="linaro":
        return LinaroToolchain(path, arch)
    if typ=="linaro_armel":
        return LinaroToolchainArmel(path, arch)

    raise Exception



