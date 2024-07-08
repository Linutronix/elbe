# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2024 Linutronix GmbH

"""
Utility to validate the contents of a created image.
The image is not booted but only mounted safely through libguestfs.

Example usage:

.. code:: python

    with Image.from_file('sda.img') as image:
        for partition in image.partitions:
            print(partition)

        with image.files() as root:
            print(root.joinpath('etc', 'hostname').read_text())
"""

import abc
import collections
import contextlib
import dataclasses
import functools
import os
import typing

import guestfs

from elbevalidate.constants import GPTPartitionType, PartitionLabel
from elbevalidate.path import Path as ImagePath


class BlockDevice(abc.ABC):
    """
    The abstract interface for block devices.
    """

    @property
    @abc.abstractmethod
    def size(self) -> int:
        """ Size in bytes. """
        pass

    @abc.abstractmethod
    def blkid(self) -> dict:
        """
        Device attributes as detected by :command:`blkid`.

        For common tags, see :manpage:`libblkid(3)`.
        """
        pass

    @abc.abstractmethod
    def files(self) -> typing.ContextManager[ImagePath]:
        """
        Access to the files as found inside the block device.
        """
        pass


def _blkid(instance):
    d = instance._gfs.blkid(instance._gfs_blockdev)
    for tag in ['DEVNAME', 'DISKSEQ']:
        d.pop(tag, None)
    return d


@dataclasses.dataclass
class Partition(BlockDevice):
    """ A single partition """

    _parent: BlockDevice = dataclasses.field(repr=False)

    number: int
    """ Number of the partition, starting at 1 """

    type: str
    """

    Type of the partition. One of

    * a GPT UUID (see :py:class:`elbevalidate.constants.GPTPartitionType`)
    * a DOS partition type number, formatted as hex
    """

    start: int
    """ Start offset of the partition in the :py:class:`Image`, in bytes."""

    _size: int

    def __post_init__(self):
        self._gfs_blockdev = self._parent._gfs_blockdev + str(self.number)

    @property
    def _gfs(self):
        return self._parent._gfs

    def blkid(self) -> dict:
        return _blkid(self)

    @property
    def size(self) -> int:
        return self._size

    @contextlib.contextmanager
    def files(self) -> collections.abc.Generator[ImagePath, None, None]:
        mountpoint = '/'
        self._gfs.mount_ro(self._gfs_blockdev, mountpoint)
        try:
            yield ImagePath(mountpoint, device=self._parent, guestfs=self._gfs)
        finally:
            self._gfs.umount(mountpoint)


@dataclasses.dataclass
class PartitionTable(collections.abc.Sequence):
    """

    List of :py:class:`Partition` inside an :py:class:`Image`.

    .. describe:: len(table)

        Number of partitions.

    .. describe:: table[index]

        Partition at index.

    .. describe:: partition in table

        Iterate over partitions.
    """

    label: PartitionLabel
    """ Type of the partition table. """

    sector_size: int
    """ Size of each sector in bytes. """

    _partitions: list[Partition]

    def __len__(self):
        return len(self._partitions)

    def __getitem__(self, key):
        return self._partitions[key]


class Image(BlockDevice):
    """
    A full system image, containing a :py:class:`PartitionTable` with :py:class:`Partition`.
    """

    def __init__(self, gfs):
        self._gfs = gfs
        self._gfs_blockdev = '/dev/sda'

    @classmethod
    @contextlib.contextmanager
    def from_file(cls, image) -> collections.abc.Generator[typing.Self, None, None]:
        """ Construct an :py:class:`Image` from a local file. """
        gfs = guestfs.GuestFS(python_return_dict=True)
        instance = cls(gfs)

        with contextlib.closing(gfs):
            gfs.add_drive_opts(os.fspath(image), readonly=True)
            gfs.launch()

            yield instance

    def blkid(self) -> dict:
        return _blkid(self)

    @functools.cached_property
    def size(self) -> int:
        return self._gfs.blockdev_getsize64(self._gfs_blockdev)

    def _get_part_type(self, parttype, partnum):
        if parttype == PartitionLabel.DOS:
            return '{:x}'.format(self._gfs.part_get_mbr_id(self._gfs_blockdev, partnum))
        elif parttype == PartitionLabel.GPT:
            return GPTPartitionType(self._gfs.part_get_gpt_type(self._gfs_blockdev, partnum))
        else:
            raise ValueError(parttype)

    @functools.cached_property
    def partitions(self) -> PartitionTable:
        """ Partitions contained in this image. """
        parttype = self._gfs.part_get_parttype(self._gfs_blockdev)
        gfs_parts = self._gfs.part_list(self._gfs_blockdev)

        partitions = [
                Partition(_parent=self,
                          number=p['part_num'], start=p['part_start'], _size=p['part_size'],
                          type=self._get_part_type(parttype, p['part_num']))
                for p in gfs_parts
        ]

        return PartitionTable(
            label=PartitionLabel(parttype),
            sector_size=self._gfs.blockdev_getss(self._gfs_blockdev),
            _partitions=partitions,
        )

    @contextlib.contextmanager
    def files(self) -> collections.abc.Generator[ImagePath, None, None]:
        roots = self._gfs.inspect_os()
        if len(roots) != 1:
            raise ValueError(roots)

        root = roots[0]

        try:
            mountpoints = self._gfs.inspect_get_mountpoints(root)
            for device, mountpoint in sorted(mountpoints.items(),
                                             key=lambda k: len(k[0])):
                self._gfs.mount_ro(mountpoint, device)

            yield ImagePath('/', device=self, guestfs=self._gfs)

        finally:
            self._gfs.umount_all()


# This is a module-level API in the stdlib, so we do the same here.
def statvfs(path: ImagePath):
    """ An equivalent of :py:func:`os.statvfs` working with :py:class:`elbevalidate.path.Path`. """
    return path._statvfs()
