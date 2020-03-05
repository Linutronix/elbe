# ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (c) 2014-2017 Torben Hohn <torben.hohn@linutronix.de>
# Copyright (c) 2014-2015, 2017 Manuel Traut <manut@linutronix.de>
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import print_function

import os
import shutil
import errno

from glob import glob
from tempfile import mkdtemp
from string import digits
import gzip

from elbepack.shellhelper import do

def size_to_int(size):
    if size[-1] in digits:
        return int(size)

    if size.endswith("M"):
        unit = 1000 * 1000
        s = size[:-1]
    elif size.endswith("MiB"):
        unit = 1024 * 1024
        s = size[:-3]
    elif size.endswith("MB"):
        unit = 1000 * 1000
        s = size[:-2]
    if size.endswith("G"):
        unit = 1000 * 1000 * 1000
        s = size[:-1]
    elif size.endswith("GiB"):
        unit = 1024 * 1024 * 1024
        s = size[:-3]
    elif size.endswith("GB"):
        unit = 1000 * 1000 * 1000
        s = size[:-2]
    if size.endswith("k"):
        unit = 1000
        s = size[:-1]
    elif size.endswith("kiB"):
        unit = 1024
        s = size[:-3]
    elif size.endswith("kB"):
        unit = 1000
        s = size[:-2]

    return int(s) * unit

class Filesystem(object):

    # pylint: disable=too-many-public-methods

    def __init__(self, path, clean=False):
        self.path = os.path.abspath(path)

        if clean:
            shutil.rmtree(self.path, True)
            os.makedirs(self.path)

    def fname(self, path):
        if path.startswith('/'):
            path = path[1:]
        return os.path.join(self.path, path)

    def open(self, path, mode="r"):
        return open(self.fname(path), mode)

    def open_gz(self, path, mode="r"):
        return gzip.open(self.fname(path), mode)

    def isdir(self, path):
        return os.path.isdir(self.fname(path))

    def islink(self, path):
        return os.path.islink(self.fname(path))

    def isfile(self, path):
        return os.path.isfile(self.fname(path))

    def exists(self, path):
        return os.path.exists(self.fname(path))

    def lexists(self, path):
        return os.path.lexists(self.fname(path))

    def mkdir(self, path):
        os.makedirs(self.realpath(path))

    def readlink(self, path):
        return os.readlink(self.fname(path))

    def realpath(self, path):

        path = path.split(os.sep)
        path.reverse()
        following = []
        real_path = [self.path]

        while path:
            candidate = path.pop()

            # Don't care
            if candidate == '' or candidate == os.curdir:
                continue

            # Can't go out of RFS
            if candidate == os.pardir:
                if following:
                    following.pop()
                if len(real_path) > 1:
                    real_path.pop()
                continue

            parent = os.sep.join(real_path)
            new_path = os.path.join(parent, candidate)
            if not os.path.islink(new_path):
                if following:
                    following.pop()
                real_path.append(candidate)
                continue

            # Circular loop; Don't follow it
            if new_path in following:
                real_path.append(candidate)
                continue

            following.append(new_path)
            link = os.readlink(new_path)

            # Reset root for absolute link
            if os.path.isabs(link):
                real_path = [self.path]

            for element in reversed(link.split(os.sep)):
                path.append(element)

        return os.sep.join(real_path)

    def symlink(self, src, path, allow_exists=False):
        try:
            os.symlink(src, self.fname(path))
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise
            elif not allow_exists:
                raise

    def stat(self, path):
        return os.stat(self.fname(path))

    def chown(self, path, uid, gid):
        os.chown(self.fname(path), uid, gid)

    def chmod(self, path, mode):
        os.chmod(self.fname(path), mode)

    def utime(self, path, times=None):
        os.utime(self.fname(path), times)

    def cat_file(self, inf):
        content = []
        try:
            f = self.open(inf)
            content = f.readlines()
            f.close()
        except IOError:
            pass
        return content

    def remove(self, path, noerr=False):
        try:
            return os.remove(self.fname(path))
        except BaseException:
            if not noerr:
                raise

    def rmtree(self, path):
        shutil.rmtree(self.fname(path))

    def listdir(self, path='', ignore=None, skiplinks=False):
        if not ignore:
            ignore = []

        retval = [
            os.path.join(
                self.path,
                path,
                x) for x in os.listdir(
                self.fname(path)) if x not in ignore]

        if skiplinks:
            retval = [
                x for x in retval if (
                    not os.path.islink(x)) and os.path.isdir(x)]

        return retval

    def glob(self, path):
        flist = glob(self.fname(path))
        for i in flist:
            if not i.startswith(self.path):
                raise IOError("Broken glob '%s'" % path)

        return flist

    def write_file(self, path, mode, cont):
        f = self.open(path, "w")
        f.write(cont)
        f.close()
        if mode is not None:
            self.chmod(path, mode)

    def append_file(self, path, content, mode=None):
        f = self.open(path, "a")
        f.write(content)
        f.close()
        if mode is not None:
            self.chmod(path, mode)

    def read_file(self, path, gzip=False):
        if gzip:
            print('read gzip '+path)
            fp = self.open_gz(path, "r")
        else:
            fp = self.open(path, "r")

        with fp:
            retval = fp.read()

        return retval

    def mkdir_p(self, newdir, mode=0o755):
        """works the way a good mkdir -p would...
                - already exists, silently complete
                - regular file in the way, raise an exception
                - parent directory(ies) does not exist, make them as well
        """
        if self.isdir(newdir):
            pass
        elif self.isfile(newdir):
            raise OSError(
                "a file with the same name as the desired "
                "dir, '%s', already exists. in RFS %s" %
                (newdir, self.path))
        else:
            self.mkdir(newdir)
            self.chmod(newdir, mode)

    def touch_file(self, fname):
        if self.exists(fname):
            self.utime(fname)
        else:
            fp = self.open(fname, "w")
            fp.close()

    def walk_files(self, directory='', exclude_dirs=None):
        if not exclude_dirs:
            exclude_dirs = []

        dirname = self.fname(directory)
        if dirname == "/":
            striplen = 0
        else:
            striplen = len(dirname)
        for dirpath, dirnames, filenames in os.walk(dirname):
            subpath = dirpath[striplen:]
            if not subpath:
                subpath = "/"

            deldirs = []
            for d in dirnames:
                dpath = os.path.join(subpath, d)
                if dpath in exclude_dirs:
                    deldirs.append(d)

            for d in deldirs:
                dirnames.remove(d)

            for f in filenames:
                fpath = os.path.join(subpath, f)
                realpath = os.path.join(dirpath, f)
                yield "/" + fpath, realpath

    def mtime_snap(self, dirname='', exclude_dirs=None):
        if not exclude_dirs:
            exclude_dirs = []
        mtime_index = {}

        for fpath, realpath in self.walk_files(dirname, exclude_dirs):
            stat = os.lstat(realpath)
            mtime_index[fpath] = stat.st_mtime

        return mtime_index

    def __disk_usage(self, directory):
        size = os.path.getsize(directory)

        for i in os.listdir(directory):
            full = os.path.join(directory, i)
            if os.path.isfile(full):
                size += os.path.getsize(full)
            elif os.path.isdir(full):
                size += self.__disk_usage(full)

        return size

    def disk_usage(self, dirname=''):
        directory = self.fname(dirname)
        return self.__disk_usage(directory)


class TmpdirFilesystem (Filesystem):
    def __init__(self, debug=False):
        tmpdir = mkdtemp()
        Filesystem.__init__(self, tmpdir)
        self.debug = debug

    def __del__(self):
        # dont delete files in debug mode
        if self.debug:
            print('leaving TmpdirFilesystem in "%s"' % self.path)
        else:
            shutil.rmtree(self.path, True)


class ImgMountFilesystem(Filesystem):
    def __init__(self, mntpoint, dev):
        Filesystem.__init__(self, mntpoint)

        self.dev = dev

    def __enter__(self):
        cmd = 'mount "%s" "%s"' % (self.dev, self.path)
        do(cmd)

        return self

    def __exit__(self, typ, value, traceback):
        do('umount "%s"' % self.path)


hostfs = Filesystem('/')
wdfs = Filesystem(os.getcwd())
