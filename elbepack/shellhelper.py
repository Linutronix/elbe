# ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (c) 2014-2015 Torben Hohn <torbenh@linutronix.de>
# Copyright (c) 2014 Ferdinand Schwenk <ferdinand.schwenk@emtrion.de>
# Copyright (c) 2016-2017 Manuel Traut <manut@linutronix.de>
#
# SPDX-License-Identifier: GPL-3.0-or-later

import os
import logging

from subprocess import Popen, PIPE, STDOUT, call

from elbepack.log import async_logging


log = logging.getLogger("log")
soap = logging.getLogger("soap")


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


def do(cmd, allow_fail=False, stdin=None, env_add=None):
    new_env = os.environ.copy()
    if env_add:
        new_env.update(env_add)

    logging.info(cmd, extra={"context":"[CMD] "})

    r, w = os.pipe()

    if stdin is None:
        p = Popen(cmd, shell=True, stdout=w, stderr=STDOUT, env=new_env)
    else:
        p = Popen(cmd, shell=True, stdin=PIPE, stdout=w, stderr=STDOUT, env=new_env)

    async_logging(r, w, soap, log)
    p.communicate(input=stdin)

    if p.returncode and not allow_fail:
        raise CommandError(cmd, p.returncode)



def chroot(directory, cmd, env_add=None, **kwargs):
    new_env = {"LANG":"C",
               "LANGUAGE":"C",
               "LC_ALL":"C"}
    if env_add:
        new_env.update(env_add)
    chcmd = 'chroot %s %s' % (directory, cmd)
    do(chcmd, env_add=new_env, **kwargs)

def get_command_out(cmd, stdin=None, allow_fail=False, env_add={}):
    new_env = os.environ.copy()
    new_env.update(env_add)

    logging.info(cmd, extra={"context":"[CMD] "})

    r, w = os.pipe()

    if stdin is None:
        p = Popen(cmd, shell=True, stdout=PIPE, stderr=w, env=new_env)
    else:
        p = Popen(cmd, shell=True, stdin=PIPE, stdout=w, stderr=STDOUT, env=new_env)

    async_logging(r, w, soap, log)
    stdout, stderr = p.communicate(input=stdin)

    if p.returncode and not allow_fail:
        raise CommandError(cmd, p.returncode)

    return stdout
