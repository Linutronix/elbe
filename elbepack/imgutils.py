# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2024 Linutronix GmbH

import contextlib
import subprocess

from elbepack.shellhelper import do, get_command_out


@contextlib.contextmanager
def losetup(dev, extra_args=[]):
    loopdev = get_command_out(
        ['losetup', '--find', '--show', '--partscan', *extra_args, dev]
    ).decode('ascii').rstrip('\n')

    try:
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
            cmd.extend(['-o', ','.join(options)])

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
