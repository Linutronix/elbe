# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2014-2017 Linutronix GmbH
# SPDX-FileCopyrightText: 2014 Ferdinand Schwenk <ferdinand.schwenk@emtrion.de>

import logging
import os
import subprocess
from io import BytesIO, TextIOWrapper
from subprocess import PIPE, Popen, STDOUT

from elbepack.log import async_logging_ctx

log = logging.getLogger('log')
soap = logging.getLogger('soap')


def system(cmd, allow_fail=False, env_add=None):
    """system() - Execute cmd in a shell.

    Throws a subprocess.CalledProcessError if cmd returns none-zero and allow_fail=False

    --

    >>> system("true")

    >>> system("false", allow_fail=True)

    >>> system("$FALSE", env_add={"FALSE":"false"}) # doctest: +ELLIPSIS
    Traceback (most recent call last):
    ...
    subprocess.CalledProcessError: ...

    """
    new_env = os.environ.copy()
    if env_add:
        new_env.update(env_add)

    subprocess.run(cmd, shell=True, env=new_env, check=not allow_fail)


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

    if isinstance(stdin, str):
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

    logging.info(log_cmd or cmd, extra={'context': '[CMD] '})

    r, w = os.pipe()

    if stdin is None:
        p = Popen(cmd, shell=True, stdout=w, stderr=STDOUT, env=new_env)
    else:
        p = Popen(cmd, shell=True, stdin=PIPE, stdout=w, stderr=STDOUT, env=new_env)

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
    do(f'chroot {directory} {cmd}', env_add=new_env, **kwargs)


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

    logging.info(cmd, extra={'context': '[CMD] '})

    r, w = os.pipe()

    if stdin is None:
        p = Popen(cmd, shell=True, stdout=PIPE, stderr=w, env=new_env)
    else:
        p = Popen(cmd, shell=True, stdin=PIPE, stdout=PIPE, stderr=w, env=new_env)

    with async_logging_ctx(r, w, soap, log):
        stdout, _ = p.communicate(input=stdin)

    if p.returncode and not allow_fail:
        raise subprocess.CalledProcessError(p.returncode, cmd)

    return stdout
