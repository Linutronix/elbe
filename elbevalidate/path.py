"""
Classes mimicking pathlib.Path-like that operate on files within a libguestfs context.
"""

import contextlib
import io
import os
import pathlib


class _PurePath:
    """
    Reference to a path inside an image.
    API is the same as of pathlib.

    Pure variant that only provides path-manipulation methods.
    """

    def __init__(self, *pathsegments, device, guestfs, root=None):
        self.device = device
        self.root = root or self
        self._p = pathlib.PurePosixPath(*pathsegments)
        self._guestfs = guestfs

    def _create_from_posixpath(self, p):
        return type(self)(
                p,
                device=self.device,
                guestfs=self._guestfs,
                root=self.root,
        )

    def joinpath(self, *pathsegments):
        return self._create_from_posixpath(self._p.joinpath(*pathsegments))

    def __truediv__(self, key):
        try:
            return self.joinpath(key)
        except TypeError:
            return NotImplemented

    def __str__(self):
        return str(self._p)

    @property
    def _path(self):
        return str(self._p)

    def __repr__(self):
        return f'{self.__class__.__name__}({str(self)})'


@contextlib.contextmanager
def _guestfs_ctx():
    """
    Map libguestfs exceptions to the matching standard Python exceptions.
    """
    _exception_mapping = [
        ('Not a directory', NotADirectoryError),
        ('No such file or directory', FileNotFoundError),
    ]

    try:
        yield
    except RuntimeError as e:
        if len(e.args) != 1 or not isinstance(e.args[0], str):
            raise

        msg = e.args[0]

        for s, t in _exception_mapping:
            if msg.endswith(': ' + s):
                raise t(msg) from e

        raise


class Path(_PurePath):
    """
    Reference to a path inside an image.
    API is the same as of pathlib.

    Normal variant containing IO functionality.
    """

    def iterdir(self):
        with _guestfs_ctx():
            for entry in self._guestfs.ls(self._path):
                yield self / entry

    def read_bytes(self):
        with _guestfs_ctx():
            return self._guestfs.read_file(self._path)

    def open(self, mode='r', buffering=-1,
             encoding=None, errors=None, newline=None):
        buf = io.BytesIO(self.read_bytes())

        if mode in ('', 'r'):
            return io.TextIOWrapper(buf, encoding=encoding,
                                    errors=errors, newline=newline)
        elif mode in ('b', 'rb'):
            return buf
        else:
            raise ValueError(f'Invalid mode {mode}')

    def read_text(self, encoding=None, errors=None):
        with self.open(encoding=encoding, errors=errors) as f:
            return f.read()

    @staticmethod
    def _convert_stat(gstat):
        return os.stat_result((
            gstat['st_mode'], gstat['st_ino'],
            gstat['st_dev'], gstat['st_nlink'],
            gstat['st_uid'], gstat['st_gid'], gstat['st_size'],
            gstat['st_atime_sec'], gstat['st_mtime_sec'],
            gstat['st_ctime_sec'],
        ))

    def stat(self):
        with _guestfs_ctx():
            return self._convert_stat(self._guestfs.statns(self._path))

    def lstat(self):
        with _guestfs_ctx():
            return self._convert_stat(self._guestfs.lstatns(self._path))

    def readlink(self):
        with _guestfs_ctx():
            return self._create_from_posixpath(self._guestfs.readlink(self._path))

    def exists(self):
        with _guestfs_ctx():
            return self._guestfs.exists(self._path)

    def is_dir(self):
        with _guestfs_ctx():
            return self._guestfs.is_dir(self._path)

    def is_file(self):
        with _guestfs_ctx():
            return self._guestfs.is_file(self._path)

    def is_mount(self):
        raise NotImplementedError()

    def is_symlink(self):
        with _guestfs_ctx():
            return self._guestfs.is_symlink(self._path)

    def is_socket(self):
        with _guestfs_ctx():
            return self._guestfs.is_socket(self._path)

    def is_fifo(self):
        with _guestfs_ctx():
            return self._guestfs.is_fifo(self._path)

    def is_block_device(self):
        with _guestfs_ctx():
            return self._guestfs.is_blockdev(self._path)

    def is_char_device(self):
        with _guestfs_ctx():
            return self._guestfs.is_chardev(self._path)

    def owner(self):
        uid = self.stat().st_uid
        passwd = self.root.joinpath('etc', 'passwd').read_text()
        for line in passwd.splitlines():
            fields = line.split(':')
            if fields[2] == str(uid):
                return fields[0]

        raise KeyError(str(uid))

    def _statvfs(self):
        with _guestfs_ctx():
            stat = self._guestfs.statvfs(self._path)

        return os.statvfs_result([
            stat['bsize'], stat['frsize'], stat['blocks'], stat['bfree'], stat['bavail'],
            stat['files'], stat['ffree'], stat['favail'],
            stat['fsid'], stat['flag'], stat['namemax'],
        ])
