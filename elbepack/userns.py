# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Linutronix GmbH

import os
import pathlib
import shutil
import sys

from elbepack.cli import CliError

CAP_SYS_ADMIN = 21

_ENTERED_MARKER = 'ELBE_USERNS_ENTERED'

_UNSHARE_ARGS = [
    'unshare',
    '--user', '--map-root-user', '--map-users=all', '--map-groups=all',
    '--mount',
    '--',
]


def have_cap_sys_admin():
    for line in pathlib.Path('/proc/self/status').read_text().splitlines():
        if line.startswith('CapEff:'):
            return bool(int(line.split()[1], 16) & (1 << CAP_SYS_ADMIN))

    return False


def ensure_mount_capability():
    if have_cap_sys_admin():
        return

    if os.environ.get(_ENTERED_MARKER):
        raise CliError(message='Still missing CAP_SYS_ADMIN after entering a new user namespace.')

    if shutil.which('unshare') is None:
        raise CliError(
            message='CAP_SYS_ADMIN is required to perform mounts, but missing. '
                    'Run as root or install unshare (util-linux) to run in a user namespace.')

    os.environ[_ENTERED_MARKER] = '1'
    os.execvp('unshare', [*_UNSHARE_ARGS, *sys.orig_argv])
