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


def _test_finetuning(root):
    # <rm>var/cache/apt/archives/*.deb</rm>
    for f in root.joinpath('var', 'cache', 'apt', 'archives').iterdir():
        assert f.suffix != '.deb'

    # <mkdir>/var/cache/test-dir</mkdir>
    assert root.joinpath('var', 'cache', 'test-dir').is_dir()

    # <mknod opts="c 0 5">/dev/null2</mknod>
    assert root.joinpath('dev', 'null2').is_char_device()

    # <cp path="/etc/hosts">/etc/hosts2</cp>
    assert root.joinpath('etc', 'hosts2').is_file()
    assert root.joinpath('etc', 'hosts2').read_text() == root.joinpath('etc', 'hosts').read_text()

    # <mv path="/etc/issue">/etc/issue2</mv>
    assert root.joinpath('etc', 'issue2').is_file()
    assert not root.joinpath('etc', 'issue').exists()

    # <ln path="/etc/hosts">/etc/hosts3</ln>
    assert root.joinpath('etc', 'hosts3').is_symlink()
    assert root.joinpath('etc', 'hosts3').readlink() == root.joinpath('etc', 'hosts')

    # <adduser groups="nogroup,staff" shell="/bin/sh" uid="2000"
    #          home="/home/nottestuser" system="true" create_home="true" create_group="true">
    #   testuser
    # </adduser>
    assert '\ntestuser:x:2000:997::/home/nottestuser:/bin/sh\n' in \
        root.joinpath('etc', 'passwd').read_text()

    # <addgroup gid="2001" system="false">testgroup</addgroup>
    assert '\ntestgroup:x:2001:\n' in root.joinpath('etc', 'group').read_text()

    # <file dst="/testfile" encoding="plain" owner="nobody" group="nogroup" mode="640">
    # 	Some cöntent wíth spe©ial characters
    # </file>
    assert root.joinpath('testfile').is_file()
    assert root.joinpath('testfile').read_text() == 'Some cöntent wíth spe©ial characters'

    # <raw_cmd>cat /etc/hosts | cat -n > /etc/hosts4</raw_cmd>
    assert root.joinpath('etc', 'hosts4').is_file()
    assert root.joinpath('etc', 'hosts4').read_text().startswith('     1\t127.0.0.1\tlocalhost\n')


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

        _test_finetuning(root)


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
