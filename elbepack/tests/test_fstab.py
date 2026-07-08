# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Linutronix GmbH

import contextlib
import pathlib
import subprocess
import xml.etree.ElementTree as ET

import pytest

from elbepack.fstab import fstabentry
from elbepack.tests.test_helpers import make_disk
from elbepack.treeutils import etree


def _entry(fstype):
    xml = f"""
    <partition>
      <source>/dev/mmcblk0p1</source>
      <label>testfs</label>
      <mountpoint>/</mountpoint>
      <fs>
        <type>{fstype}</type>
      </fs>
    </partition>
    """
    return fstabentry(None, etree(None, string=xml).root)


FSTYPES_NEEDING_PRESIZED_TARGET = {
    'ext2', 'ext3', 'ext4', 'btrfs', 'f2fs', 'vfat',
}

IMAGE_SIZE = 320 * 1024 * 1024


def _get_schema_fstypes():
    schema_path = pathlib.Path(__file__).parent.parent / 'schema' / 'dbsfed.xsd'
    tree = ET.parse(schema_path)
    root = tree.getroot()

    xs_ns = 'http://www.w3.org/2001/XMLSchema'
    ns = {'xs': xs_ns}

    for simple_type in root.findall('.//xs:simpleType', ns):
        if simple_type.get('name') == 'fs_type_restriction':
            fstypes = []
            for enum in simple_type.findall('.//xs:enumeration', ns):
                fstypes.append(enum.get('value'))
            return fstypes

    raise RuntimeError('Could not find fs_type_restriction in schema')


NON_MKFS_FSTYPES = {
    'ubifs',
    'tmpfs',
    'debugfs',
    'configfs',
    'devpts',
    'proc',
    'sysfs',
    'vfat',
    'btrfs',
    'devtmpfs',
    'swap',
}
ALL_FSTYPES = [
    pytest.param(fstype, id=fstype)
    for fstype in _get_schema_fstypes()
    if fstype not in NON_MKFS_FSTYPES
]


@pytest.fixture
def reference_tree():
    return pathlib.Path(__file__).parent / 'data' / 'reference_tree'


@contextlib.contextmanager
def _mkfs_and_mount(elbevalidate, fstype, tmp_path, src):
    image = tmp_path / 'image.img'
    disk = tmp_path / 'disk.img'
    try:
        if fstype in FSTYPES_NEEDING_PRESIZED_TARGET:
            subprocess.run(['truncate', '-s', str(IMAGE_SIZE), str(image)], check=True)

        try:
            needs_cp = _entry(fstype).mkfs(str(image), str(src) + '/.')
        except FileNotFoundError:
            pytest.skip(f'mkfs tool not available for {fstype}')
        assert not needs_cp

        make_disk(disk, [image.read_bytes()])

        with elbevalidate.Image.from_file(disk) as img:
            assert len(img.partitions) == 1
            with img.partitions[0].files() as root:
                yield root
    finally:
        image.unlink(missing_ok=True)
        disk.unlink(missing_ok=True)


@pytest.mark.parametrize('fstype', ALL_FSTYPES)
def test_mkfs_roundtrips_reference_tree(fstype, elbevalidate, tmp_path, reference_tree):
    with _mkfs_and_mount(elbevalidate, fstype, tmp_path, reference_tree) as root:
        assert root.joinpath('.hidden').read_text() == 'hidden\n'
        assert root.joinpath('visible.txt').read_text() == 'data\n'
        assert root.joinpath('subdir', 'nested.txt').read_text() == 'nested-data\n'


@pytest.mark.parametrize('fstype', ALL_FSTYPES)
def test_mkfs_empty_tree_does_not_fail(fstype, elbevalidate, tmp_path):
    src = tmp_path / 'src'
    src.mkdir()

    with _mkfs_and_mount(elbevalidate, fstype, tmp_path, src) as root:
        entries = [p.name for p in root.iterdir() if p.name != 'lost+found']
        assert entries == []
