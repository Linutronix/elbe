# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2013-2014, 2017-2018 Linutronix GmbH

import importlib
import os
import pathlib
import struct
import subprocess
import tempfile
import textwrap

import pytest


@pytest.fixture
def elbevalidate():
    for image in pathlib.Path('/boot').glob('vmlinuz-*'):
        if not os.access(image, os.R_OK):
            pytest.skip(f'Kernel image {image} is not readable')

    try:
        return importlib.import_module('elbevalidate', package=__name__)
    except ModuleNotFoundError as e:
        if e.name == 'guestfs':
            pytest.skip(f'module {e.name} not found')
        else:
            raise


def _round_to(n, g):
    return n + (g - (n % g))


def _make_disk(path, parts):
    """ Create a basic MBR partition table. """

    if len(parts) > 4:
        raise ValueError(parts)

    data_offset = 2 * 1024 * 1024  # 2MiB

    header = bytearray(512)
    current_data = data_offset

    for i, part in enumerate(parts):
        partbytes = bytearray(16)

        rounded_size = _round_to(len(part), 512)

        partbytes[0x04] = 0x83
        partbytes[0x08:0x0C] = struct.pack('<I', current_data // 512)
        partbytes[0x0C:0x10] = struct.pack('<I', rounded_size // 512)

        part_start = 0x01BE + 16 * i
        header[part_start:part_start + 16] = partbytes

        current_data += rounded_size

    header[0x01FE] = 0x55
    header[0x01FF] = 0xAA

    with path.open('wb') as f:
        f.write(header)
        f.write(b'\x00' * (data_offset - len(header)))

        for part in parts:
            rounded_size = _round_to(len(part), 512)
            f.write(part)
            f.write(bytearray(rounded_size - len(part)))


def _make_partition(path):
    assert path.is_dir()

    with tempfile.NamedTemporaryFile() as t:
        subprocess.run(
            ['mksquashfs', path, t.name, '-noappend'],
            check=True, capture_output=True,
        )

        return pathlib.Path(t.name).read_bytes()


def test_elbevalidate(elbevalidate, tmp_path):
    part1_dir = tmp_path / 'part1'
    part1_dir.mkdir()

    part2_dir = tmp_path / 'part2'
    part2_dir.mkdir()

    part1_dir.joinpath('foo').write_text('foo')
    part2_dir.joinpath('bar').write_text('bar')

    etc = part1_dir / 'etc'
    etc.mkdir()

    etc.joinpath('fstab').write_text(textwrap.dedent("""
        /dev/sda1   /       squashfs    defaults    0   0
        /dev/sda2   /data   squashfs    defaults    0   0
    """))

    bin_ = part1_dir / 'bin'
    bin_.mkdir()

    data = part1_dir / 'data'
    data.mkdir()

    disk_file = tmp_path / 'disk.img'
    part1 = _make_partition(part1_dir)
    part2 = _make_partition(part2_dir)
    _make_disk(disk_file, [part1, part2])

    with elbevalidate.Image.from_file(disk_file) as image:

        assert image.size == disk_file.stat().st_size

        image_blkid = image.blkid()
        assert image_blkid['PTTYPE'] == 'dos'

        assert len(image.partitions) == 2

        part0 = image.partitions[0]
        assert part0.type == '83'
        assert part0.size == len(part1) + 512
        assert image.read_at(4, part0.start) == b'hsqs'  # SquashFS superblock

        part0_blkid = part0.blkid()
        assert part0_blkid['TYPE'] == 'squashfs'
        assert 'DEVNAME' not in part0_blkid

        with part0.files() as root:
            path = root.joinpath('foo.tar.gz')
            assert path.suffix == '.gz'
            assert path.suffixes == ['.tar', '.gz']
            assert path.stem == 'foo.tar'
            assert path.parent == root.root
            assert path.parents == [root.root]

            assert root.joinpath('foo').exists()
            assert not root.joinpath('bar').exists()

            statvfs = elbevalidate.statvfs(root)
            assert statvfs.f_blocks == 1
            assert statvfs.f_files == 6
            assert statvfs.f_bfree == 0
            assert statvfs.f_ffree == 0

        with image.files() as root:
            assert root.joinpath('foo').exists()
            assert not root.joinpath('bar').exists()
            assert root.joinpath('data', 'bar').exists()
