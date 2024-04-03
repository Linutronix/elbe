# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2020-2021 Linutronix GmbH

import pathlib

import pytest

from elbepack.directories import run_elbe


def _test_file_path(name):
    return pathlib.Path(__file__).parents[2].joinpath('tests', name)


@pytest.mark.parametrize(('inp', 'out'), [
    ('preproc-01.xml', 'preproc-01.out.xml'),
    ('preproc-02.xml', 'preproc-02.out.xml'),
])
def test_preproc(inp, out, tmp_path):
    actual = tmp_path / (inp + '.out')
    run_elbe([
        'preprocess',
        '-z', '0',
        '-o', actual,
        _test_file_path(inp),
    ], check=True)
    with open(_test_file_path(out)) as expected, actual.open() as a:
        assert a.read() == expected.read()
