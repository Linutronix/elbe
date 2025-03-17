# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2024 Linutronix GmbH

import itertools
import os
import socket

import pytest

from elbepack.main import run_elbe_subcommand


def _test_cases():
    return [
        os.path.join('tests', fname)
        for fname
        in os.listdir('tests')
        if fname.endswith('.xml')
    ]


def _examples():
    return [
        os.path.join('examples', fname)
        for fname
        in os.listdir('examples')
        if fname.endswith('.xml')
    ]


def _root_cause(e):
    while True:
        if e.__context__ is None:
            return e

        e = e.__context__


@pytest.mark.parametrize('f', itertools.chain(_test_cases(), _examples()))
def test_validate(f, tmp_path):
    p = tmp_path / 'preprocessed.xml'
    try:
        run_elbe_subcommand(['preprocess', '-o', p, f])
    except Exception as e:
        root_cause = _root_cause(e)
        if isinstance(root_cause, socket.gaierror) and root_cause.errno == socket.EAI_AGAIN:
            pytest.skip('Network is unavailable')
        raise
    run_elbe_subcommand(['validate', p])
