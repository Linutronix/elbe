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

import sys
import os
import string

from tempfile import mkdtemp

control_template_string = """Package: ${name}
Version: ${version}
Section: main
Priority: optional
Architecture: ${arch}
Maintainer: elbe-devel@linutronix.de
Description: ${description}
Depends: ${deps}
Multi-Arch: same
"""

control_template = string.Template(control_template_string)

def gen_controlfile(name, version, arch, description, deps):
    d = dict( name=name, version=version, arch=arch, description=description, deps=deps )
    return control_template.substitute(d)

def write_file( fname, mode, cont ):
    f = file( fname, "w" )
    f.write(cont)
    f.close()
    os.chmod( fname, mode )


def build_binary_deb( name, arch, version, description, files, deps, target_dir ):
    tmpdir   = mkdtemp()
    pkgfname = "%s_%s_%s" % (name, version, arch)
    pkgdir = os.path.join( tmpdir, pkgfname )

    os.system( 'mkdir -p "%s"' % os.path.join( pkgdir, "DEBIAN" ) )
    write_file( os.path.join( pkgdir, "DEBIAN" , "control" ), 0644, gen_controlfile(name, version, arch, description, deps) )

    for (fname, instpath) in files:
        full_instpath = os.path.join( pkgdir, instpath )
        os.system( 'mkdir -p "%s"' % full_instpath )
        os.system( 'cp -a "%s" "%s"' % (fname, full_instpath) )
    
    os.system( 'dpkg-deb --build "%s"' % pkgdir )

    os.system( 'cp -v "%s" "%s"' % (os.path.join( tmpdir, pkgfname + ".deb" ), target_dir) )

    os.system( 'rm -r "%s"' % tmpdir )

    return pkgfname+".deb"

