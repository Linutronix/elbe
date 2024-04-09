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
    @property
    @abc.abstractmethod
    def size(self) -> int:
        pass

    @abc.abstractmethod
    def blkid(self) -> dict:
        pass

    @abc.abstractmethod
    def files(self) -> typing.ContextManager[ImagePath]:
        pass


def _blkid(instance):
    d = instance._gfs.blkid(instance._gfs_blockdev)
    for tag in ['DEVNAME', 'DISKSEQ']:
        d.pop(tag, None)
    return d


@dataclasses.dataclass
class Partition(BlockDevice):
    _parent: BlockDevice = dataclasses.field(repr=False)
    number: int
    type: str
    start: int
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
class PartitionTable:
    label: PartitionLabel
    sector_size: int
    _partitions: list[Partition]

    def __len__(self):
        return len(self._partitions)

    def __getitem__(self, key):
        return self._partitions[key]


class Image(BlockDevice):
    def __init__(self, gfs):
        self._gfs = gfs
        self._gfs_blockdev = '/dev/sda'

    @classmethod
    @contextlib.contextmanager
    def from_file(cls, image) -> collections.abc.Generator[typing.Self, None, None]:
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
    return path._statvfs()
