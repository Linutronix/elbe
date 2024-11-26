# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2019 Linutronix GmbH

import os
import subprocess

from elbepack.shellhelper import do


class Packer:

    def pack_file(self, _builddir, _fname):
        raise NotImplementedError('abstract method called')


class NoPacker(Packer):

    def pack_file(self, _builddir, fname):
        return fname


class InPlacePacker(Packer):

    def __init__(self, cmd, suffix):

        self.cmd = cmd
        self.suffix = suffix

    def pack_file(self, builddir, fname):
        try:
            fpath = os.path.join(builddir, fname)
            do(f'{self.cmd} "{fpath}"')
        except subprocess.CalledProcessError:
            # in case of an error, we just return None
            # which means, that the orig file does not
            # exist anymore
            return None

        return fname + self.suffix


class TarArchiver(Packer):

    def __init__(self, flag, suffix):
        self.flag = flag
        self.suffix = suffix

    def pack_file(self, builddir, fname):
        try:
            fpath = os.path.join(builddir, fname)
            dirname = os.path.dirname(fpath)
            basename = os.path.basename(fpath)
            archname = fpath + self.suffix
            do(
                f'tar --create --verbose --sparse {self.flag} '
                f'--file "{archname}" --directory "{dirname}" "{basename}"')
            do(f'rm -f "{fpath}"')
        except subprocess.CalledProcessError:
            # in case of an error, we just return None
            # which means, that the orig file does not
            # exist anymore.
            #
            # Even if it actually exists, it might be
            # much to big to download it and remove
            # the sparsity.
            return None

        return fname + self.suffix


packers = {'none': NoPacker(),
           'gzip': InPlacePacker('gzip -f', '.gz'),
           'zstd': InPlacePacker('zstd -T0', '.zst'),
           'tar':  TarArchiver('--auto-compress', '.tar'),
           'tarxz': TarArchiver('--use-compress-program="xz -T0 -M40%"', '.tar.xz'),
           'targz': TarArchiver('--auto-compress', '.tar.gz'),
           'tarzstd': TarArchiver('--use-compress-program="zstd -T0"', '.tar.zst'),
           }

default_packer = packers['targz']
