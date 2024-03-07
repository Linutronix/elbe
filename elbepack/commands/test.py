# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2020 Linutronix GmbH

# elbepack/commands/test.py - Elbe unit test wrapper

from elbepack.shellhelper import command_out


class ElbeTestException(Exception):

    def __init__(self, cmd, ret, out):
        super().__init__()
        self.cmd = cmd
        self.ret = ret
        self.out = out

    def __str__(self):
        return f'ElbeTestException: \"{self.cmd}\" returns {self.ret}\noutput:\n{self.out}'


def system(cmd, allow_fail=False):
    ret, out = command_out(cmd)
    if ret != 0 and not allow_fail:
        raise ElbeTestException(cmd, ret, out)
