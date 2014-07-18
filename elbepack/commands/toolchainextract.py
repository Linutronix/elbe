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

from optparse import OptionParser
import sys
import os
import string

from tempfile import mkdtemp

from elbepack.xmldefaults import ElbeDefaults
from elbepack.repomanager import ToolchainRepo
from elbepack.debpkg import build_binary_deb
from elbepack.toolchain import get_toolchain
from elbepack.asciidoclog import StdoutLog


def run_command( argv ):
    oparser = OptionParser(usage="usage: %prog toolchainextract [options]")
    oparser.add_option( "-p", "--path", dest="path",
                        help="path to toolchain" )
    oparser.add_option( "-o", "--output", dest="output",
                        help="output repository path" )
    oparser.add_option( "-c", "--codename", dest="codename",
                        help="distro codename for repository" )
    oparser.add_option( "-b", "--buildtype", dest="buildtype",
                        help="Override the buildtype" )
    (opt,args) = oparser.parse_args(argv)

    if not opt.path:
        oparser.print_help()
        return 0
    if not opt.output:
        oparser.print_help()
        return 0
    if not opt.codename:
        oparser.print_help()
        return 0
    if not opt.buildtype:
        oparser.print_help()
        return 0

    defaults = ElbeDefaults( opt.buildtype )
    
    toolchain = get_toolchain( defaults["toolchaintype"], opt.path, defaults["arch"] )

    tmpdir   = mkdtemp()

    for lib in toolchain.pkg_libs:
        files = toolchain.get_files_for_pkg( lib )

        pkglibpath = os.path.join( "usr/lib", defaults["triplet"] )
        fmap = [ (f, pkglibpath) for f in files ]

        build_binary_deb( lib, defaults["arch"], defaults["toolchainver"], lib + " extracted from toolchain", fmap, toolchain.pkg_deps[lib], tmpdir )

    pkgs = os.listdir(tmpdir)

    repo = ToolchainRepo( defaults["arch"], opt.codename, opt.output, StdoutLog() )

    for p in pkgs:
        repo.includedeb( os.path.join(tmpdir, p) )
    
    os.system( 'rm -r "%s"' % tmpdir )
        



