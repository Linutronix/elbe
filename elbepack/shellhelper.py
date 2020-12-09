# ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (c) 2014-2015 Torben Hohn <torbenh@linutronix.de>
# Copyright (c) 2014 Ferdinand Schwenk <ferdinand.schwenk@emtrion.de>
# Copyright (c) 2016-2017 Manuel Traut <manut@linutronix.de>
#
# SPDX-License-Identifier: GPL-3.0-or-later

import os
import logging

from subprocess import Popen, PIPE, STDOUT, call

from io import TextIOWrapper, BytesIO

from elbepack.log import async_logging

log = logging.getLogger("log")
soap = logging.getLogger("soap")


class CommandError(Exception):

    def __init__(self, cmd, returncode):
        super(CommandError, self).__init__(cmd, returncode)
        self.returncode = returncode
        self.cmd = cmd

    def __str__(self):
        return "Error: %d returned from Command %s" % (
            self.returncode, self.cmd)

def system(cmd, allow_fail=False, env_add=None):
    """system() - Execute cmd in a shell.

    Throws a CommandError if cmd returns none-zero and allow_fail=False

    --

    >>> system("true")

    >>> system("false", allow_fail=True)

    >>> system("$FALSE", env_add={"FALSE":"false"}) # doctest: +ELLIPSIS
    Traceback (most recent call last):
    ...
    elbepack.shellhelper.CommandError: ...

    """
    new_env = os.environ.copy()
    if env_add:
        new_env.update(env_add)

    ret = call(cmd, shell=True, env=new_env)

    if ret != 0:
        if not allow_fail:
            raise CommandError(cmd, ret)


def command_out(cmd, stdin=None, output=PIPE, env_add=None):
    """command_out() - Execute cmd in a shell.

    Returns a tuple with the exitcode and the output of cmd.

    --

    >>> command_out("true")
    (0, '')

    >>> command_out("$TRUE && true", env_add={"TRUE":"true"})
    (0, '')

    >>> command_out("cat -", stdin=b"ELBE")
    (0, 'ELBE')

    >>> command_out("2>&1 cat -", stdin=b"ELBE")
    (0, 'ELBE')

    >>> command_out("2>&1 cat -", stdin="ELBE")
    (0, 'ELBE')

    >>> command_out("false")
    (1, '')

    """
    new_env = os.environ.copy()
    if env_add:
        new_env.update(env_add)

    if type(stdin) == str:
        stdin = stdin.encode()

    if stdin is None:
        p = Popen(cmd, shell=True,
                  stdout=output, stderr=STDOUT, env=new_env)
        out, _ = p.communicate()
    else:
        p = Popen(cmd, shell=True,
                  stdout=output, stderr=STDOUT, stdin=PIPE, env=new_env)
        out, _ = p.communicate(input=stdin)

    out = TextIOWrapper(BytesIO(out), encoding='utf-8', errors='replace').read()

    return p.returncode, out


def system_out(cmd, stdin=None, allow_fail=False, env_add=None):
    """system_out() - Wrapper around command_out().

    On failure, raises an exception if allow_fail=False, on success,
    returns the output of cmd.

    --

    >>> system_out("false") # doctest: +ELLIPSIS
    Traceback (most recent call last):
    ...
    elbepack.shellhelper.CommandError: ...

    >>> system_out("false", allow_fail=True)
    ''

    """
    code, out = command_out(cmd, stdin=stdin, env_add=env_add)

    if code != 0:
        if not allow_fail:
            raise CommandError(cmd, code)

    return out


def command_out_stderr(cmd, stdin=None, env_add=None):
    """command_out_stderr() - Execute cmd in a shell.

    Returns a tuple of the exitcode, stdout and stderr of cmd.

    --

    >>> command_out_stderr("$TRUE && cat -", stdin=b"ELBE", env_add={"TRUE":"true"})
    (0, 'ELBE', '')

    >>> command_out_stderr("1>&2 cat - && false", stdin=b"ELBE")
    (1, '', 'ELBE')

    >>> command_out_stderr("1>&2 cat - && false", stdin="ELBE")
    (1, '', 'ELBE')

    >>> command_out_stderr("true")
    (0, '', '')

    """
    new_env = os.environ.copy()
    if env_add:
        new_env.update(env_add)

    if type(stdin) == str:
        stdin = stdin.encode()

    if stdin is None:
        p = Popen(cmd, shell=True,
                  stdout=PIPE, stderr=PIPE, env=new_env)
        output, stderr = p.communicate()
    else:
        p = Popen(cmd, shell=True,
                  stdout=PIPE, stderr=PIPE, stdin=PIPE, env=new_env)
        output, stderr = p.communicate(input=stdin)

    output = TextIOWrapper(BytesIO(output), encoding='utf-8', errors='replace').read()
    stderr = TextIOWrapper(BytesIO(stderr), encoding='utf-8', errors='replace').read()

    return p.returncode, output, stderr


def system_out_stderr(cmd, stdin=None, allow_fail=False, env_add=None):
    """system_out_stderr() - Wrapper around command_out_stderr()

    Throws CommandError if cmd failed and allow_fail=False.  Otherwise,
    returns the stdout and stderr of cmd.

    --

    >>> system_out_stderr("false") # doctest: +ELLIPSIS
    Traceback (most recent call last):
    ...
    elbepack.shellhelper.CommandError: ...

    >>> system_out_stderr("cat - && false", allow_fail=True, stdin=b"ELBE")
    ('ELBE', '')

    >>> system_out_stderr("1>&2 cat -", allow_fail=True, stdin=b"ELBE")
    ('', 'ELBE')

    >>> system_out_stderr("1>&2 cat -", allow_fail=True, stdin="ELBE")
    ('', 'ELBE')
    """
    code, out, err = command_out_stderr(cmd, stdin, env_add)

    if code != 0:
        if not allow_fail:
            raise CommandError(cmd, code)

    return out, err


def do(cmd, allow_fail=False, stdin=None, env_add=None):
    """do() - Execute cmd in a shell and redirect outputs to logging.

    Throws a CommandError if cmd failed with allow_Fail=False.

    --

    Let's redirect the loggers to current stdout
    >>> import sys
    >>> from elbepack.log import open_logging
    >>> open_logging({"streams":sys.stdout})

    >>> do("true")
    [CMD] true

    >>> do("false", allow_fail=True)
    [CMD] false

    >>> do("cat -", stdin=b"ELBE")
    [CMD] cat -

    >>> do("cat - && false", stdin=b"ELBE") # doctest: +ELLIPSIS
    Traceback (most recent call last):
    ...
    elbepack.shellhelper.CommandError: ...

    >>> do("false") # doctest: +ELLIPSIS
    Traceback (most recent call last):
    ...
    elbepack.shellhelper.CommandError: ...
    """

    new_env = os.environ.copy()
    if env_add:
        new_env.update(env_add)

    if type(stdin) == str:
        stdin = stdin.encode()

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
    """chroot() - Wrapper around do().

    --

    Let's redirect the loggers to current stdout

    >>> import sys
    >>> from elbepack.log import open_logging
    >>> open_logging({"streams":sys.stdout})

    >>> chroot("/", "true") # doctest: +ELLIPSIS
    Traceback (most recent call last):
    ...
    elbepack.shellhelper.CommandError: ...
    """

    new_env = {"LANG":"C",
               "LANGUAGE":"C",
               "LC_ALL":"C"}
    if env_add:
        new_env.update(env_add)
    chcmd = 'chroot %s %s' % (directory, cmd)
    do(chcmd, env_add=new_env, **kwargs)

def get_command_out(cmd, stdin=None, allow_fail=False, env_add=None):
    """get_command_out() - Like do() but returns stdout.

    --

    Let's quiet the loggers

    >>> import os
    >>> from elbepack.log import open_logging
    >>> open_logging({"files":os.devnull})

    >>> get_command_out("echo ELBE")
    b'ELBE\\n'

    >>> get_command_out("false") # doctest: +ELLIPSIS
    Traceback (most recent call last):
    ...
    elbepack.shellhelper.CommandError: ...

    >>> get_command_out("false", allow_fail=True)
    b''

    >>> get_command_out("cat -", stdin=b"ELBE", env_add={"TRUE":"true"})
    b'ELBE'

    >>> get_command_out("cat -", stdin="ELBE", env_add={"TRUE":"true"})
    b'ELBE'
    """

    new_env = os.environ.copy()

    if env_add:
        new_env.update(env_add)

    if type(stdin) == str:
        stdin = stdin.encode()

    logging.info(cmd, extra={"context":"[CMD] "})

    r, w = os.pipe()

    if stdin is None:
        p = Popen(cmd, shell=True, stdout=PIPE, stderr=w, env=new_env)
    else:
        p = Popen(cmd, shell=True, stdin=PIPE, stdout=PIPE, stderr=w, env=new_env)

    async_logging(r, w, soap, log)
    stdout, _ = p.communicate(input=stdin)

    if p.returncode and not allow_fail:
        raise CommandError(cmd, p.returncode)

    return stdout
