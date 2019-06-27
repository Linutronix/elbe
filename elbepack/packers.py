# ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (c) 2019 Torben Hohn <torben.hohn@linutronix.de>
#
# SPDX-License-Identifier: GPL-3.0-or-later

import os
from elbepack.shellhelper import CommandError, do


class Packer(object):
    # pylint: disable=too-few-public-methods
    def pack_file(self, _builddir, _fname):
        raise NotImplementedError('abstract method called')


class NoPacker(Packer):
    # pylint: disable=too-few-public-methods
    def pack_file(self, _builddir, fname):
        return fname


class InPlacePacker(Packer):
    # pylint: disable=too-few-public-methods
    def __init__(self, cmd, suffix):

        self.cmd = cmd
        self.suffix = suffix

    def pack_file(self, builddir, fname):
        try:
            fpath = os.path.join(builddir, fname)
            do('%s "%s"' % (self.cmd, fpath))
        except CommandError:
            # in case of an error, we just return None
            # which means, that the orig file does not
            # exist anymore
            return None

        return fname + self.suffix


class TarArchiver(Packer):
    # pylint: disable=too-few-public-methods
    def __init__(self, flag, suffix):
        self.flag = flag
        self.suffix = suffix

    def pack_file(self, builddir, fname):
        try:
            fpath = os.path.join(builddir, fname)
            dirname = os.path.dirname(fpath)
            basename = os.path.basename(fpath)
            archname = fpath + self.suffix
            do('tar cv%sf "%s" --sparse -C "%s" "%s"' %
               (self.flag, archname, dirname, basename))
            do('rm -f "%s"' % fpath)
        except CommandError:
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
           'tar':  TarArchiver('', '.tar'),
           'tarxz': TarArchiver('J', '.tar.xz'),
           'targz': TarArchiver('z', '.tar.gz')}

default_packer = packers['targz']
