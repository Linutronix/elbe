# ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (c) 2014-2015 Torben Hohn <torbenh@linutronix.de>
# Copyright (c) 2014 Ferdinand Schwenk <ferdinand.schwenk@emtrion.de>
# Copyright (c) 2016-2017 Manuel Traut <manut@linutronix.de>
#
# SPDX-License-Identifier: GPL-3.0-or-later

import os
from subprocess import Popen, PIPE, STDOUT, call


class CommandError(Exception):
    def __init__(self, cmd, returncode):
        Exception.__init__(self)
        self.returncode = returncode
        self.cmd = cmd

    def __repr__(self):
        return "Error: %d returned from Command %s" % (
            self.returncode, self.cmd)


def system(cmd, allow_fail=False, env_add=None):
    new_env = os.environ.copy()
    if env_add:
        new_env.update(env_add)

    ret = call(cmd, shell=True, env=new_env)

    if ret != 0:
        if not allow_fail:
            raise CommandError(cmd, ret)


def command_out(cmd, stdin=None, output=PIPE, env_add=None):
    new_env = os.environ.copy()
    if env_add:
        new_env.update(env_add)

    if stdin is None:
        p = Popen(cmd, shell=True,
                  stdout=output, stderr=STDOUT, env=new_env)
        out, _ = p.communicate()
    else:
        p = Popen(cmd, shell=True,
                  stdout=output, stderr=STDOUT, stdin=PIPE, env=new_env)
        out, _ = p.communicate(input=stdin)

    return p.returncode, out


def system_out(cmd, stdin=None, allow_fail=False, env_add=None):
    code, out = command_out(cmd, stdin=stdin, env_add=env_add)

    if code != 0:
        if not allow_fail:
            raise CommandError(cmd, code)

    return out


def command_out_stderr(cmd, stdin=None, env_add=None):
    new_env = os.environ.copy()
    if env_add:
        new_env.update(env_add)

    if stdin is None:
        p = Popen(cmd, shell=True,
                  stdout=PIPE, stderr=PIPE, env=new_env)
        output, stderr = p.communicate()
    else:
        p = Popen(cmd, shell=True,
                  stdout=PIPE, stderr=PIPE, stdin=PIPE, env=new_env)
        output, stderr = p.communicate(input=stdin)

    return p.returncode, output, stderr


def system_out_stderr(cmd, stdin=None, allow_fail=False, env_add=None):
    code, out, err = command_out_stderr(cmd, stdin, env_add)

    if code != 0:
        if not allow_fail:
            raise CommandError(cmd, code)

    return out, err
