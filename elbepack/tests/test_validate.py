# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2024 Linutronix GmbH

import itertools
import os

from elbepack.directories import run_elbe

import pytest


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


@pytest.mark.parametrize('f', itertools.chain(_test_cases(), _examples()))
def test_validate(f, tmp_path):
    p = tmp_path / 'preprocessed.xml'
    run_elbe(['preprocess', '-o', p, f], check=True)
    run_elbe(['validate', p], check=True)
