# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2014-2017 Linutronix GmbH
# SPDX-FileCopyrightText: 2014 Ferdinand Schwenk <ferdinand.schwenk@emtrion.de>

import logging
import os
import shlex
import subprocess
from subprocess import PIPE, Popen, STDOUT

from elbepack.log import async_logging_ctx

log = logging.getLogger('log')
soap = logging.getLogger('soap')


def _is_shell_cmd(cmd):
    return isinstance(cmd, str)


def _log_cmd(cmd):
    if _is_shell_cmd(cmd):
        return cmd
    else:
        return shlex.join(cmd)


def do(cmd, allow_fail=False, stdin=None, env_add=None, log_cmd=None):
    """do() - Execute cmd in a shell and redirect outputs to logging.

    Throws a subprocess.CalledProcessError if cmd returns none-zero and allow_fail=False

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
    subprocess.CalledProcessError: ...

    >>> do("false") # doctest: +ELLIPSIS
    Traceback (most recent call last):
    ...
    subprocess.CalledProcessError: ...
    """

    new_env = os.environ.copy()
    if env_add:
        new_env.update(env_add)

    if isinstance(stdin, str):
        stdin = stdin.encode()

    shell = _is_shell_cmd(cmd)

    logging.info(log_cmd or _log_cmd(cmd), extra={'context': '[CMD] '})

    r, w = os.pipe()

    if stdin is None:
        p = Popen(cmd, shell=shell, stdout=w, stderr=STDOUT, env=new_env)
    else:
        p = Popen(cmd, shell=shell, stdin=PIPE, stdout=w, stderr=STDOUT, env=new_env)

    with async_logging_ctx(r, w, soap, log):
        p.communicate(input=stdin)

    if p.returncode and not allow_fail:
        raise subprocess.CalledProcessError(p.returncode, cmd)


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
    subprocess.CalledProcessError: ...
    """

    new_env = {'LANG': 'C',
               'LANGUAGE': 'C',
               'LC_ALL': 'C'}
    if env_add:
        new_env.update(env_add)

    if _is_shell_cmd(cmd):
        do(['chroot', directory, '/bin/sh', '-c', cmd], env_add=new_env, **kwargs)
    else:
        do(['chroot', directory] + cmd, env_add=new_env, **kwargs)


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
    subprocess.CalledProcessError: ...

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

    if isinstance(stdin, str):
        stdin = stdin.encode()

    shell = _is_shell_cmd(cmd)

    logging.info(_log_cmd(cmd), extra={'context': '[CMD] '})

    r, w = os.pipe()

    if stdin is None:
        p = Popen(cmd, shell=shell, stdout=PIPE, stderr=w, env=new_env)
    else:
        p = Popen(cmd, shell=shell, stdin=PIPE, stdout=PIPE, stderr=w, env=new_env)

    with async_logging_ctx(r, w, soap, log):
        stdout, _ = p.communicate(input=stdin)

    if p.returncode and not allow_fail:
        raise subprocess.CalledProcessError(p.returncode, cmd)

    return stdout


def env_add(d):
    env = os.environ.copy()
    env.update(d)
    return env
