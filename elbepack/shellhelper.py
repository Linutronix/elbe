# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2014-2017 Linutronix GmbH
# SPDX-FileCopyrightText: 2014 Ferdinand Schwenk <ferdinand.schwenk@emtrion.de>

import contextlib
import logging
import os
import shlex
import subprocess

from elbepack.log import async_logging_ctx


"""
Forward to elbe logging system.
"""
ELBE_LOGGING = object()


def _is_shell_cmd(cmd):
    return isinstance(cmd, str)


def _log_cmd(cmd):
    if _is_shell_cmd(cmd):
        return cmd
    else:
        return shlex.join(map(os.fspath, cmd))


def run(cmd, /, *, check=True, log_cmd=None, **kwargs):
    """
    Like subprocess.run() but
     * defaults to check=True
     * logs the executed command
     * accepts ELBE_LOGGING for stdout and stderr

    --

    Let's quiet the loggers

    >>> import os
    >>> import sys
    >>> from elbepack.log import open_logging
    >>> cleanup = open_logging(streams=os.devnull)
    >>> run(['echo', 'ELBE'])
    CompletedProcess(args=['echo', 'ELBE'], returncode=0)

    >>> run(['echo', 'ELBE'], capture_output=True)
    CompletedProcess(args=['echo', 'ELBE'], returncode=0, stdout=b'ELBE\\n', stderr=b'')

    >>> run(['false']) # doctest: +ELLIPSIS
    Traceback (most recent call last):
    ...
    subprocess.CalledProcessError: ...

    >>> run('false', check=False).returncode
    1

    >>> run(['cat', '-'], input=b'ELBE', capture_output=True).stdout
    b'ELBE'

    >>> run(['echo', 'ELBE'], stdout=ELBE_LOGGING)
    CompletedProcess(args=['echo', 'ELBE'], returncode=0)
    >>> cleanup()

    Let's redirect the loggers to current stdout

    >>> from elbepack.log import open_logging
    >>> cleanup = open_logging(streams=sys.stdout)
    >>> run(['echo', 'ELBE'], stdout=ELBE_LOGGING)
    [CMD] echo ELBE
    ELBE
    ELBE
    CompletedProcess(args=['echo', 'ELBE'], returncode=0)

    >>> run(['echo', 'ELBE'], capture_output=True)
    CompletedProcess(args=['echo', 'ELBE'], returncode=0, stdout=b'ELBE\\n', stderr=b'')
    >>> cleanup()
    """
    stdout = kwargs.pop('stdout', None)
    stderr = kwargs.pop('stderr', None)

    with contextlib.ExitStack() as stack:
        if stdout is ELBE_LOGGING or stderr is ELBE_LOGGING:
            log_fd = stack.enter_context(async_logging_ctx())
            if stdout is ELBE_LOGGING:
                stdout = log_fd
            if stderr is ELBE_LOGGING:
                stderr = log_fd

            logging.info(log_cmd or _log_cmd(cmd), extra={'context': '[CMD] '})

        return subprocess.run(cmd, stdout=stdout, stderr=stderr, check=check, **kwargs)


def do(cmd, /, *, env_add=None, **kwargs):
    """do() - Execute cmd in a shell and redirect outputs to logging.

    Throws a subprocess.CalledProcessError if cmd returns none-zero and check=True

    --

    Let's redirect the loggers to current stdout
    >>> import sys
    >>> from elbepack.log import open_logging
    >>> cleanup = open_logging(streams=sys.stdout)
    >>> do("true")
    [CMD] true

    >>> do("false", check=False)
    [CMD] false

    >>> do("cat -", input=b"ELBE")
    [CMD] cat -

    >>> do("cat - && false", input=b"ELBE") # doctest: +ELLIPSIS
    Traceback (most recent call last):
    ...
    subprocess.CalledProcessError: ...

    >>> do("false") # doctest: +ELLIPSIS
    Traceback (most recent call last):
    ...
    subprocess.CalledProcessError: ...
    >>> cleanup()
    """

    new_env = os.environ.copy()
    if env_add:
        new_env.update(env_add)

    run(cmd, shell=_is_shell_cmd(cmd), env=new_env, stdout=ELBE_LOGGING, stderr=subprocess.STDOUT,
        **kwargs)


def _target_path(directory):
    FALLBACK_PATH = '/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin'

    try:
        login_defs = open(os.path.join(directory, 'etc/login.defs'))
    except FileNotFoundError:
        return FALLBACK_PATH

    with login_defs:
        for line in login_defs:
            fields = line.split(maxsplit=1)
            if len(fields) == 2 and fields[0] == 'ENV_SUPATH' and fields[1].startswith('PATH='):
                return fields[1].removeprefix('PATH=')

    return FALLBACK_PATH


class _Mount:
    # This is not using contextlib.contextmanager as it will be pass to our
    # RPCAPTCache which uses the pickle serialization.
    # The generator by contextlib.contextmanager is not compatible with pickle.
    def __init__(self, device, target, *, bind=False, type=None, options=None, log_output=True,
                 force_writable=False):
        self.log_output = log_output
        self.target = target

        cmd = ['mount']
        if bind:
            cmd.append('--bind')

        if options is not None:
            cmd.extend(['-o', options])

        if force_writable:
            cmd.append('--rw')

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


def chroot(directory, cmd, /, *, env_add=None, **kwargs):
    """chroot() - Wrapper around do().

    --

    Let's redirect the loggers to current stdout

    >>> import sys
    >>> from elbepack.log import open_logging
    >>> cleanup = open_logging(streams=sys.stdout)
    >>> chroot("/", "false") # doctest: +ELLIPSIS
    Traceback (most recent call last):
    ...
    subprocess.CalledProcessError: ...
    >>> cleanup()
    """

    new_env = {'LANG': 'C',
               'LANGUAGE': 'C',
               'LC_ALL': 'C',
               'PATH': _target_path(directory)}
    if env_add:
        new_env.update(env_add)

    if _is_shell_cmd(cmd):
        do(['/usr/sbin/chroot', directory, '/bin/sh', '-c', cmd], env_add=new_env, **kwargs)
    else:
        do(['/usr/sbin/chroot', directory] + cmd, env_add=new_env, **kwargs)


def env_add(d):
    env = os.environ.copy()
    env.update(d)
    return env


def get_env_with_sbin():
    sbin_dirs = ['/sbin', '/usr/sbin', '/usr/local/sbin']
    return {'PATH': os.pathsep.join([os.environ.get('PATH', ''), *sbin_dirs])}
