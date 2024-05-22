#!/usr/bin/env python3

import sys
import textwrap

import elbevalidate
import elbevalidate.pytest


def test_build_directory_contents(build_dir):
    created_files = list([p.name for p in build_dir.iterdir()])
    for f in [
            'elbe-report.txt',
            'licence-chroot.txt',
            'licence-chroot.xml',
            'licence-target.txt',
            'licence-target.xml',
            'log.txt',
            'sda.img',
            'source.xml',
            'validation.txt',
            ]:

        assert f in created_files


def _test_rfs_partition(part):
    assert part.number == 1
    assert part.start == 1 * 1024 * 1024
    assert part.size == 799 * 1024 * 1024
    assert part.type == '83'

    blkid = part.blkid()
    assert blkid['USAGE'] == 'filesystem'
    assert blkid['TYPE'] == 'ext4'
    assert blkid['LABEL'] == 'rfs'

    with part.files() as root:
        statvfs = elbevalidate.statvfs(root)
        assert statvfs.f_bfree * statvfs.f_bsize > 300 * 1024 * 1024

        assert root.joinpath('etc', 'hostname').read_text() == 'validation-image'
        assert root.joinpath('etc', 'mailname').read_text() == 'validation-image.elbe-ci'
        assert not root.joinpath('etc', 'resolv.conf').exists()
        assert root.joinpath('etc', 'os-release').read_text().strip() == textwrap.dedent("""
            PRETTY_NAME="Debian GNU/Linux 12 (bookworm)"
            NAME="Debian GNU/Linux"
            VERSION_ID="12"
            VERSION="12 (bookworm)"
            VERSION_CODENAME=bookworm
            ID=debian
            HOME_URL="https://www.debian.org/"
            SUPPORT_URL="https://www.debian.org/support"
            BUG_REPORT_URL="https://bugs.debian.org/"
        """).strip()
        assert root.joinpath('etc', 'apt', 'sources.list').read_text() in [
            # With and without source CDROM
            'deb-src [] http://deb.debian.org/debian bookworm main\n'
            'deb [arch=amd64] http://deb.debian.org/debian bookworm main',

            'deb [arch=amd64] http://deb.debian.org/debian bookworm main',
        ]

        sources_list_d = root.joinpath('etc', 'apt', 'sources.list.d')
        assert sources_list_d.is_dir()
        assert len(list(sources_list_d.iterdir())) == 0

        getty_service = root.joinpath('etc', 'systemd', 'system', 'getty.target.wants',
                                      'serial-getty@ttyS0.service')
        assert getty_service.is_symlink()
        assert str(getty_service.readlink()) == '/lib/systemd/system/serial-getty@.service'


def test_image(build_dir):
    with elbevalidate.Image.from_file(build_dir / 'sda.img') as img:
        assert img.size == 800 * 1024 * 1024

        blkid = img.blkid()
        assert blkid['PTTYPE'] == 'dos'

        partitions = img.partitions
        assert len(partitions) == 1

        _test_rfs_partition(partitions[0])


if __name__ == '__main__':
    elbevalidate.pytest.run_with_pytest(__file__, sys.argv[1])
