# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2014-2017 Linutronix GmbH

from optparse import OptionParser
from tempfile import mkdtemp

import os
import sys

from elbepack.xmldefaults import ElbeDefaults
from elbepack.repomanager import ToolchainRepo
from elbepack.debpkg import build_binary_deb
from elbepack.toolchain import get_toolchain
from elbepack.log import elbe_logging


def run_command(argv):
    oparser = OptionParser(usage='usage: %prog toolchainextract [options]')
    oparser.add_option('-p', '--path', dest='path',
                       help='path to toolchain')
    oparser.add_option('-o', '--output', dest='output',
                       help='output repository path')
    oparser.add_option('-c', '--codename', dest='codename',
                       help='distro codename for repository')
    oparser.add_option('-b', '--buildtype', dest='buildtype',
                       help='Override the buildtype')
    (opt, _) = oparser.parse_args(argv)

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

    defaults = ElbeDefaults(opt.buildtype)

    toolchain = get_toolchain(
        defaults['toolchaintype'],
        opt.path,
        defaults['arch'])

    tmpdir = mkdtemp()

    for lib in toolchain.pkg_libs:
        files = toolchain.get_files_for_pkg(lib)

        pkglibpath = os.path.join('usr/lib', defaults['triplet'])
        fmap = [(f, pkglibpath) for f in files]

        build_binary_deb(
            lib,
            defaults['arch'],
            defaults['toolchainver'],
            lib +
            ' extracted from toolchain',
            fmap,
            toolchain.pkg_deps[lib],
            tmpdir)

    pkgs = os.listdir(tmpdir)

    with elbe_logging({'streams': sys.stdout}):

        repo = ToolchainRepo(defaults['arch'],
                             opt.codename,
                             opt.output)

        for p in pkgs:
            repo.includedeb(os.path.join(tmpdir, p))

        repo.finalize()
        os.system(f'rm -r "{tmpdir}"')

    return 0
