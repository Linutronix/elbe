# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2019 Linutronix GmbH

import abc
import os
import subprocess

from elbepack.shellhelper import do


class Packer(abc.ABC):

    @abc.abstractmethod
    def pack_file(self, _builddir, _fname):
        ...

    @abc.abstractmethod
    def packed_filename(self, fname):
        ...


class NoPacker(Packer):

    def pack_file(self, _builddir, fname):
        return fname

    def packed_filename(self, fname):
        return fname


class InPlacePacker(Packer):

    def __init__(self, cmd, suffix):

        self.cmd = cmd
        self.suffix = suffix

    def pack_file(self, builddir, fname):
        try:
            fpath = os.path.join(builddir, fname)
            do([*self.cmd, fpath])
        except subprocess.CalledProcessError:
            # in case of an error, we just return None
            # which means, that the orig file does not
            # exist anymore
            return None

        return self.packed_filename(fname)

    def packed_filename(self, fname):
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
            do([
                'tar', '--create', '--verbose', '--sparse', self.flag,
                '--file', archname, '--directory', dirname, basename,
            ])
            do(['rm', '-f', fpath])
        except subprocess.CalledProcessError:
            # in case of an error, we just return None
            # which means, that the orig file does not
            # exist anymore.
            #
            # Even if it actually exists, it might be
            # much to big to download it and remove
            # the sparsity.
            return None

        return self.packed_filename(fname)

    def packed_filename(self, fname):
        return fname + self.suffix


class AndroidSparsePacker(Packer):
    def pack_file(self, builddir, fname):
        try:
            fpath = os.path.join(builddir, fname)
            do(['img2simg', fpath, fpath + '.simg'])
            do(['rm', '-f', fpath])
            return self.packed_filename(fname)
        except subprocess.CalledProcessError:
            # in case of an error, we just return None
            # which means, that the orig file does not
            # exist anymore
            return None

    def packed_filename(self, fname):
        return fname + '.simg'


packers = {'none': NoPacker(),
           'gzip': InPlacePacker(['gzip', '-f'], '.gz'),
           'zstd': InPlacePacker(['zstd', '-T0'], '.zst'),
           'tar':  TarArchiver('--auto-compress', '.tar'),
           'tarxz': TarArchiver('--use-compress-program=xz -T0 -M40%', '.tar.xz'),
           'targz': TarArchiver('--auto-compress', '.tar.gz'),
           'tarzstd': TarArchiver('--use-compress-program=zstd -T0', '.tar.zst'),
           'android-sparse': AndroidSparsePacker(),
           }

default_packer = packers['tarxz']


def find_packed_image(directory, image):
    for packer in packers.values():
        packed_filename = packer.packed_filename(image)
        img_name = directory / packed_filename
        if img_name.exists():
            return img_name
