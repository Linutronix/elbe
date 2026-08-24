# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2013-2014, 2017-2018 Linutronix GmbH

import pathlib
import subprocess
import tarfile
import tempfile
import textwrap

from elbepack.tests.test_helpers import make_disk


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
    make_disk(disk_file, [part1, part2])

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


def test_tarbpallpath(elbevalidate, tmp_path):
    def _check_dir(_dir):
        dir_content = [str(i) for i in _dir.iterdir()]
        assert '{}/test-file'.format(_dir) in dir_content
        assert '{}/test-link'.format(_dir) in dir_content

        test_file = _dir / 'test-file'
        assert test_file.exists()
        assert test_file.is_file()
        assert not test_file.is_dir()
        assert not test_file.is_symlink()
        assert test_file.stat().st_size == 12
        assert test_file.read_bytes() == b'Test content'

        test_link = _dir / 'test-link'
        assert test_link.exists()
        assert not test_link.is_file()
        assert not test_link.is_dir()
        assert test_link.is_symlink()
        assert str(test_link.readlink()) == 'test-file'

    tarball = tmp_path / 'test-tarball.tar'

    tarball_dir = tmp_path / 'tarball-dir'
    tarball_dir.mkdir()

    tarball_dir.joinpath('test-file').write_text('Test content')
    tarball_dir.joinpath('test-link').symlink_to('test-file')

    with tarfile.open(tarball, 'w') as tar:
        tar.add(tarball_dir, arcname='dir1')
        tar.add(tarball_dir, arcname='./dir2')

    with elbevalidate.Tar.from_file(tarball) as tar:
        with tar.files() as root:
            top_dirs = [str(i) for i in root.iterdir()]
            assert top_dirs == ['dir1', 'dir2']

            dir1 = root / 'dir1'
            assert dir1.exists()
            assert dir1.is_dir()
            dir2 = root / 'dir2'
            assert dir2.exists()
            assert dir2.is_dir()
            dir3 = root / 'dir3'
            assert not dir3.exists()

            _check_dir(dir1)
            _check_dir(dir2)
