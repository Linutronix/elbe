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

from treeutils import etree
from optparse import OptionParser
import datetime
import apt
import sys
import os
import string

from mako.template import Template
from mako import exceptions

import elbepack

from tempfile import mkdtemp

def read_file( fname ):
    f = file( fname, "r" )
    d = f.read()
    f.close()
    return d

def write_file( fname, mode, cont ):
    f = file( fname, "w" )
    f.write(cont)
    f.close()
    os.chmod( fname, mode )

control_template_string = """Package: ${name}
Version: ${version}
Section: main
Priority: optional
Architecture: ${arch}
Maintainer: elbe-devel@linutronix.de
Description: kernel/initrd package for elbe
"""

control_template = string.Template(control_template_string)

def gen_controlfile(name, version, arch):
    d = dict( name=name, version=version, arch=arch )
    return control_template.substitute(d)

def run_command( argv ):
    oparser = OptionParser(usage="usage: %prog initrdpack [options]")
    oparser.add_option( "-n", "--name", dest="name",
                        help="name of package" )
    oparser.add_option( "-a", "--architecture", dest="arch",
                        help="architecture" )
    oparser.add_option( "-k", "--kernel", dest="kernel",
                        help="name of kernel" )
    oparser.add_option( "-i", "--initrd", dest="initrd",
                        help="name of initrd" )
    oparser.add_option( "-I", "--initrd-cdrom", dest="cinitrd",
                        help="name of initrd" )
    oparser.add_option( "-v", "--version", dest="version",
                        help="name of version" )
    oparser.add_option( "-c", "--codename", dest="codename",
                        help="debian distro codename" )
    (opt,args) = oparser.parse_args(argv)

    if not opt.arch:
        oparser.print_help()
        return 0
    if not opt.kernel:
        oparser.print_help()
        return 0
    if not opt.initrd:
        oparser.print_help()
        return 0
    if not opt.version:
        oparser.print_help()
        return 0
    if not opt.codename:
        oparser.print_help()
        return 0

    tmpdir   = mkdtemp()
    pkgfname = "%s_%s_%s" % (opt.name, opt.version, opt.arch)
    pkgdir = os.path.join( tmpdir, pkgfname )

    rdpath = os.path.join( pkgdir, "opt/elbe/initrd" )
    os.system( 'mkdir -p "%s"' % rdpath )
    os.system( 'mkdir -p "%s"' % os.path.join( pkgdir, "DEBIAN" ) )

    os.system( 'cp "%s" "%s"' % (opt.kernel, os.path.join(rdpath,"vmlinuz")) )
    os.system( 'cp "%s" "%s"' % (opt.initrd, os.path.join(rdpath,"initrd.gz")) )
    os.system( 'cp "%s" "%s"' % (opt.cinitrd, os.path.join(rdpath,"initrd-cdrom.gz")) )

    write_file( os.path.join( pkgdir, "DEBIAN" , "control" ), 0644, gen_controlfile(opt.name, opt.version, opt.arch) )
    os.system( 'dpkg-deb --build "%s"' % pkgdir )

    os.system( 'cp -v "%s" .' % os.path.join( tmpdir, pkgfname + ".deb" ) )

    os.system( 'rm -r "%s"' % tmpdir )


if __name__ == "__main__":
    run_command( sys.argv[1:] )
