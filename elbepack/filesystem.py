# ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (c) 2014-2017 Torben Hohn <torben.hohn@linutronix.de>
# Copyright (c) 2014-2015, 2017 Manuel Traut <manut@linutronix.de>
#
# SPDX-License-Identifier: GPL-3.0-or-later

import os
import shutil

from glob import glob
from tempfile import mkdtemp


class Filesystem(object):
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

    def isdir(self, path):
        return os.path.isdir(self.fname(path))

    def islink(self, path):
        return os.path.islink(self.fname(path))

    def isfile(self, path):
        return os.path.isfile(self.fname(path))

    def exists(self, path):
        return os.path.exists(self.fname(path))

    def mkdir(self, path):
        os.makedirs(self.fname(path))

    def symlink(self, src, path, allow_exists=False):
        try:
            os.symlink(src, self.fname(path))
        except OSError as e:
            if e.errno != os.errno.EEXIST:
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

    def listdir(self, path='', ignore=[], skiplinks=False):
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
        self.chmod(path, mode)

    def read_file(self, path):
        fp = self.open(path, "r")
        retval = fp.read()
        fp.close()
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

    def walk_files(self, directory='', exclude_dirs=[]):
        dirname = self.fname(directory)
        if dirname == "/":
            striplen = 0
        else:
            striplen = len(dirname)
        for dirpath, dirnames, filenames in os.walk(dirname):
            subpath = dirpath[striplen:]
            if len(subpath) == 0:
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

    def mtime_snap(self, dirname='', exclude_dirs=[]):
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
    def __init__(self):
        tmpdir = mkdtemp()
        Filesystem.__init__(self, tmpdir)

    def __del__(self):
        shutil.rmtree(self.path, True)


hostfs = Filesystem('/')
wdfs = Filesystem(os.getcwd())
