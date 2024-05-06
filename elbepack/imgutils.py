# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2024 Linutronix GmbH

import contextlib

from elbepack.shellhelper import do, get_command_out


@contextlib.contextmanager
def losetup(dev, extra_args=[]):
    loopdev = get_command_out(
        f'losetup --find --show --partscan {" ".join(extra_args)} "{dev}"'
    ).decode('ascii').rstrip('\n')

    try:
        yield loopdev
    finally:
        do(f'losetup --detach {loopdev}', check=False)
