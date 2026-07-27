# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2024 Linutronix GmbH

import contextlib
import fcntl
import pathlib
import subprocess

from elbepack.shellhelper import ELBE_LOGGING, do, run


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
        partitions = [
            '/dev/' + entry.name
            for entry in pathlib.Path('/sys/class/block', device_name).iterdir()
            if entry.name.startswith(device_name)
        ]

    # All partitions need to be mentioned explicitly.
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
