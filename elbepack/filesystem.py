# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2014-2017 Linutronix GmbH

import errno
import gzip
import os
import shutil
from glob import glob
from string import digits
from tempfile import mkdtemp

from elbepack.shellhelper import do


def size_to_int(size):
    if size[-1] in digits:
        return int(size)

    if size.endswith('M'):
        unit = 1000 * 1000
        s = size[:-1]
    elif size.endswith('MiB'):
        unit = 1024 * 1024
        s = size[:-3]
    elif size.endswith('MB'):
        unit = 1000 * 1000
        s = size[:-2]
    if size.endswith('G'):
        unit = 1000 * 1000 * 1000
        s = size[:-1]
    elif size.endswith('GiB'):
        unit = 1024 * 1024 * 1024
        s = size[:-3]
    elif size.endswith('GB'):
        unit = 1000 * 1000 * 1000
        s = size[:-2]
    if size.endswith('k'):
        unit = 1000
        s = size[:-1]
    elif size.endswith('kiB'):
        unit = 1024
        s = size[:-3]
    elif size.endswith('kB'):
        unit = 1000
        s = size[:-2]

    return int(s) * unit


class Filesystem:

    def __init__(self, path, clean=False):
        """
        >>> os.path.isdir(this.path)
        True
        """

        self.path = os.path.abspath(path)

        if clean:
            shutil.rmtree(self.path, True)
            os.makedirs(self.path)

    def fname(self, path):
        """
        >>> expect = os.path.join(this.path, "fname")
        >>> this.fname("/fname") == expect == this.fname("fname")
        True
        """
        if path.startswith('/'):
            path = path[1:]
        return os.path.join(self.path, path)

    def open(self, path, mode='r'):
        """
        >>> this.open("open") # doctest: +ELLIPSIS
        Traceback (most recent call last):
        ...
        FileNotFoundError: [Errno 2] ...

        >>> this.open("open", mode="w") # doctest: +ELLIPSIS
        <_io.TextIOWrapper ...>

        >>> _.close()
        """
        return open(self.fname(path), mode)

    def open_gz(self, path, mode='r'):
        """
        >>> this.open_gz("open_gz") # doctest: +ELLIPSIS
        Traceback (most recent call last):
        ...
        FileNotFoundError: [Errno 2] ...

        >>> this.open_gz("open_gz", mode="w") # doctest: +ELLIPSIS
        <gzip _io.BufferedWriter ...>

        >>> _.close()
        """
        return gzip.open(self.fname(path), mode)

    def isdir(self, path):
        """
        >>> this.isdir("isdir")
        False

        >>> os.makedirs(this.fname("isdir"))
        >>> this.isdir("isdir")
        True
        """
        return os.path.isdir(self.fname(path))

    def islink(self, path):
        """
        >>> this.islink("islink")
        False

        >>> os.symlink("target", this.fname("islink"))
        >>> this.islink("islink")
        True
        """
        return os.path.islink(self.fname(path))

    def isfile(self, path):
        """
        >>> this.isfile("isfile")
        False

        >>> open(this.fname("isfile"), mode="w").close()
        >>> this.isfile("isfile")
        True
        """
        return os.path.isfile(self.fname(path))

    def exists(self, path):
        """
        >>> this.exists("exists")
        False

        >>> os.symlink("broken", this.fname("exixsts-broken-link"))
        >>> this.exists("exists-broken-link")
        False

        >>> open(this.fname("exists"), mode="w").close()
        >>> this.exists("exists")
        True
        """
        return os.path.exists(self.fname(path))

    def lexists(self, path):
        """
        >>> this.lexists("lexists")
        False

        >>> os.symlink("target", this.fname("lexists"))
        >>> os.path.lexists(this.fname("lexists"))
        True
        """
        return os.path.lexists(self.fname(path))

    def mkdir(self, path):
        """
        >>> os.path.isdir(this.fname("mkdir"))
        False
        >>> this.mkdir("mkdir")
        >>> os.path.isdir(this.fname("mkdir"))
        True
        """
        os.makedirs(self.realpath(path))

    def readlink(self, path):
        """
        >>> this.symlink("target", "readlink")
        >>> this.readlink("readlink")
        'target'
        """
        return os.readlink(self.fname(path))

    def realpath(self, path):
        """
        >>> this.realpath(".") == this.path
        True

        >>> this.realpath("..") == this.path
        True

        >>> this.realpath("/realpath") == this.fname("/realpath")
        True

        >>> this.symlink("/target", "realpath-abs-symlink")
        >>> this.realpath("realpath-abs-symlink") == this.fname("/target")
        True

        >>> this.symlink("target", "/realpath-symlink")
        >>> this.realpath("realpath-symlink") == this.fname("/target")
        True

        >>> this.symlink(".././realpath-symlink", "realpath-multi-symlink")
        >>> this.realpath("realpath-multi-symlink") == this.fname("/target")
        True

        >>> this.symlink("realpath-loop-A", "realpath-loop-B")
        >>> this.symlink("realpath-loop-B", "realpath-loop-A")
        >>> this.realpath("realpath-loop-A") == this.fname("/realpath-loop-A")
        True

        >>> this.realpath("realpath-loop-B") == this.fname("realpath-loop-B")
        True
        """
        path = path.split(os.sep)
        path.reverse()
        following = []
        real_path = [self.path]

        while path:
            candidate = path.pop()

            # Don't care
            if candidate in ('', os.curdir):
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
        """
        >>> this.symlink("target", "symlink-link")
        >>> os.readlink(this.fname("symlink-link"))
        'target'

        >>> this.symlink("target", "symlink-link") # doctest: +ELLIPSIS
        Traceback (most recent call last):
        ...
        FileExistsError: [Errno 17] ...

        >>> os.readlink(this.fname("not-a-link")) # doctest: +ELLIPSIS
        Traceback (most recent call last):
        ...
        FileNotFoundError: [Errno 2] ...

        >>> this.symlink("target", "symlink-link", allow_exists=True)
        """
        try:
            os.symlink(src, self.fname(path))
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise
            if not allow_exists:
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
        """
        >>> this.remove("remove") # doctest: +ELLIPSIS
        Traceback (most recent call last):
        ...
        FileNotFoundError: [Errno 2] ...

        >>> this.remove("remove", noerr=True)

        >>> open(this.fname("remove"), "w").close()
        >>> this.remove("remove")

        >>> this.lexists("remove")
        False
        """
        try:
            return os.remove(self.fname(path))
        except BaseException:
            if not noerr:
                raise

    def rmtree(self, path):
        """
        >>> this.mkdir("/rmtree/rmtree")
        >>> this.rmtree("/rmtree")
        >>> this.lexists("/rmtree/rmtree")
        False
        >>> this.lexists("/rmtree")
        False
        """
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
                raise IOError(f"Broken glob '{path}'")

        return flist

    @staticmethod
    def _write_file(path, f, cont, mode):
        f.write(cont)
        f.close()
        if mode is not None:
            os.chmod(path, mode)

    def write_file(self, path, mode, cont):
        path = self.realpath(path)
        self._write_file(path, open(path, 'w'), cont, mode)

    def append_file(self, path, cont, mode=None):
        path = self.realpath(path)
        self._write_file(path, open(path, 'a'), cont, mode)

    def read_file(self, path, gz=False):
        path = self.realpath(path)
        if gz:
            fp = gzip.open(path, 'r')
        else:
            fp = open(path, 'r')

        with fp:
            retval = fp.read()

        return retval

    def mkdir_p(self, newdir, mode=0o755):
        """works the way a good mkdir -p would...
                - already exists, silently complete
                - regular file in the way, raise an exception
                - parent directory(ies) does not exist, make them as well

        --
        >>> this.mkdir_p("mkdir_p/foo/bar")
        >>> this.isdir("mkdir_p")
        True

        >>> this.isdir("mkdir_p/foo")
        True

        >>> this.isdir("mkdir_p/foo/bar")
        True

        >>> open(this.fname("mkdir_p/foo/bar/baz"), "w").close()

        >>> this.mkdir_p("mkdir_p/foo/bar/baz") # doctest: +ELLIPSIS
        Traceback (most recent call last):
        ...
        OSError: a file with the same name as the desired dir, ...
        """
        if self.isdir(newdir):
            pass
        elif self.isfile(newdir):
            raise OSError(
                'a file with the same name as the desired '
                f"dir, '{newdir}', already exists. in RFS {self.path}")
        else:
            self.mkdir(newdir)
            self.chmod(newdir, mode)

    def touch_file(self, fname):
        if self.exists(fname):
            self.utime(fname)
        else:
            fp = self.open(fname, 'w')
            fp.close()

    def walk_files(self, directory='', exclude_dirs=None):
        if not exclude_dirs:
            exclude_dirs = []

        dirname = self.fname(directory)
        if dirname == '/':
            striplen = 0
        else:
            striplen = len(dirname)
        for dirpath, dirnames, filenames in os.walk(dirname):
            subpath = dirpath[striplen:]
            if not subpath:
                subpath = '/'

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
                yield '/' + fpath, realpath

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
            print(f'leaving TmpdirFilesystem in "{self.path}"')
        else:
            self.delete()

    def delete(self):
        shutil.rmtree(self.path, True)

    def __enter__(self):
        return self

    def __exit__(self, exec_type, exec_value, tb):
        shutil.rmtree(self.path)
        return False


class ImgMountFilesystem(Filesystem):
    def __init__(self, mntpoint, dev):
        Filesystem.__init__(self, mntpoint)

        self.dev = dev

    def __enter__(self):
        do(f'mount "{self.dev}" "{self.path}"')

        return self

    def __exit__(self, typ, value, traceback):
        do(f'umount "{self.path}"')


hostfs = Filesystem('/')
wdfs = Filesystem(os.getcwd())
