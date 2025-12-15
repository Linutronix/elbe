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
    subprocess.check_call(['udevadm', 'wait', device, *partitions])


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


class _Mount:
    # This is not using contextlib.contextmanager as it will be pass to our
    # RPCAPTCache which uses the pickle serialization.
    # The generator by contextlib.contextmanager is not compatible with pickle.
    def __init__(self, device, target, *, bind=False, type=None, options=None, log_output=True):
        self.log_output = log_output
        self.target = target

        cmd = ['mount']
        if bind:
            cmd.append('--bind')

        if options is not None:
            cmd.extend(['-o', options])

        if type is not None:
            cmd.extend(['-t', type])

        if device is None:
            device = 'none'

        cmd.extend([device, target])

        self.cmd = cmd

    def _run_cmd(self, cmd, *args, **kwargs):
        if self.log_output:
            do(cmd, *args, **kwargs)
        else:
            subprocess.run(cmd, *args, **kwargs)

    def __enter__(self):
        self._run_cmd(self.cmd)

    def __exit__(self, exc_type, exc_value, traceback):
        self._run_cmd(['umount', self.target], check=False)


mount = _Mount


def dd(args, /, **kwargs):
    do(['dd', *[f'{k}={v}' for k, v in args.items()]], **kwargs)
