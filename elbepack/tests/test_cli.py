# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2024 Linutronix GmbH

import io
import re
import textwrap

import elbepack.cli


def _strip_file_and_lineno(s):
    s = re.sub(
        re.escape(__file__) + r':\d+',
        '__file__:00',
        s,
    )
    s = re.sub(
        r'"' + re.escape(__file__) + r'", line \d+',
        '"__file__", line 00',
        s,
    )
    return s


def _test_excepthook(exception, exitcode, output, *, verbose):
    buf = io.StringIO()

    assert exception.__traceback__
    actual_exitcode = elbepack.cli.format_exception(
        exception,
        output=buf, verbose=verbose, base_module=elbepack,
    )

    assert actual_exitcode == exitcode
    assert _strip_file_and_lineno(buf.getvalue()) == output


def _test_exception():
    try:
        raise ValueError('some error')
    except ValueError as e:
        return e


def test_excepthook_without_info():
    _test_excepthook(
        _test_exception(),
        1,
        '__file__:00: ValueError: some error\n',
        verbose=False,
    )


def test_excepthook_without_info_verbose():
    _test_excepthook(
        _test_exception(),
        1,
        textwrap.dedent("""
        Traceback (most recent call last):
          File "__file__", line 00, in _test_exception
            raise ValueError('some error')
        ValueError: some error
        """).lstrip(),
        verbose=True,
    )


def test_excepthook_with_info():
    _test_excepthook(
        elbepack.cli.with_cli_details(
            _test_exception(),
            exitcode=4,
            message='some message',
        ),
        4,
        'some message\n__file__:00: ValueError: some error\n',
        verbose=False,
    )


def test_excepthook_with_info_verbose():
    _test_excepthook(
        elbepack.cli.with_cli_details(
            _test_exception(),
            exitcode=4,
            message='some message',
        ),
        4,
        textwrap.dedent("""
        some message
        Traceback (most recent call last):
          File "__file__", line 00, in _test_exception
            raise ValueError('some error')
        ValueError: some error
        """).lstrip(),
        verbose=True,
    )
