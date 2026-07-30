# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2024 Linutronix GmbH

import contextlib
import fcntl
import os
import pathlib
import stat
import subprocess

from elbepack.shellhelper import ELBE_LOGGING, do, run


def _udev_available():
    return pathlib.Path('/run/udev/control').is_socket()


def _mknod_from_sysfs(device_name):
    devpath = f'/dev/{device_name}'
    if os.path.exists(devpath):
        return

    dev_attr = pathlib.Path('/sys/class/block', device_name, 'dev').read_text().strip()
    major, minor = (int(x) for x in dev_attr.split(':'))
    with contextlib.suppress(FileExistsError):
        os.mknod(devpath, mode=0o660 | stat.S_IFBLK, device=os.makedev(major, minor))
        os.chmod(devpath, 0o660)


def _symlink_by_uuid_from_blkid(device_name):
    devpath = f'/dev/{device_name}'
    blkid = subprocess.run(
        ['blkid', '-s', 'UUID', '-o', 'value', devpath],
        stdout=subprocess.PIPE, check=False,
    )
    uuid = blkid.stdout.decode('ascii').strip()
    if blkid.returncode != 0 or not uuid:
        return

    by_uuid_dir = pathlib.Path('/dev/disk/by-uuid')
    by_uuid_dir.mkdir(parents=True, exist_ok=True)
    with contextlib.suppress(FileExistsError):
        (by_uuid_dir / uuid).symlink_to(devpath)


def _wait_on_udev_for_device_and_partitions(device):
    # The callers expect the udev symlinks of the loop device and its
    # partitions to be present.

    device_name = pathlib.Path(device).name
    with open(device) as f:
        # The partition entries in /sys/class/blocks are created by the kernel
        # and guaranteed to exist after "losetup" returns.
        # However udev processing triggers a rescan of the partitions, removing
        # the entries for a short time. Prevent udev from doing so while we iterate.
        fcntl.flock(f, fcntl.LOCK_EX)
        partition_names = [
            entry.name
            for entry in pathlib.Path('/sys/class/block', device_name).iterdir()
            if entry.name.startswith(device_name)
        ]

    if not _udev_available():
        for name in (device_name, *partition_names):
            _mknod_from_sysfs(name)
            _symlink_by_uuid_from_blkid(name)
        return

    # All partitions need to be mentioned explicitly.
    partitions = ['/dev/' + name for name in partition_names]
    subprocess.run(['udevadm', 'wait', device, *partitions],
                   check=True, timeout=30)


@contextlib.contextmanager
def losetup(dev, extra_args=[]):
    loopdev = run(
        ['losetup', '--find', '--show', '--partscan', *extra_args, dev],
        stdout=subprocess.PIPE, stderr=ELBE_LOGGING,
    ).stdout.decode('ascii').rstrip('\n')

    try:
        _wait_on_udev_for_device_and_partitions(loopdev)
        yield loopdev
    finally:
        do(['losetup', '--detach', loopdev], check=False)


def dd(args, /, **kwargs):
    do(['dd', *[f'{k}={v}' for k, v in args.items()]], **kwargs)
