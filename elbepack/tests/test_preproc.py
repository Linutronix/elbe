# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2020-2021 Linutronix GmbH

import pathlib
import tarfile

import pytest

from elbepack.directories import run_elbe_subcommand


def _test_file_path(name):
    return pathlib.Path(__file__).parents[2].joinpath('tests', name)


@pytest.mark.parametrize(('inp', 'out', 'variant'), [
    ('preproc-01.xml', 'preproc-01.out.xml', None),
    ('preproc-02.xml', 'preproc-02.out.xml', None),
    ('preproc-variants.xml', 'preproc-variants-none.out.xml', None),
    ('preproc-variants.xml', 'preproc-variants-variant1.out.xml', 'variant1'),
    ('preproc-variants.xml', 'preproc-variants-variant2.out.xml', 'variant2'),
    ('preproc-variants.xml', 'preproc-variants-variant1,variant2.out.xml', 'variant1,variant2'),
])
def test_preproc(inp, out, variant, tmp_path):
    actual = tmp_path / (inp + '.out')
    run_elbe_subcommand([
        'preprocess',
        '-z', '0',
        *(['-v', variant] if variant else []),
        '-o', actual,
        _test_file_path(inp),
    ])
    with open(_test_file_path(out)) as expected, actual.open() as a:
        assert a.read() == expected.read()


def test_archive(tmp_path):
    preprocessed = tmp_path / 'preprocessed.xml'
    run_elbe_subcommand([
        'preprocess', '-z', '0',
        '-o', preprocessed,
        _test_file_path('simple-validation-image.xml'),
    ])

    archive = tmp_path / 'archive.tar.bz2'
    run_elbe_subcommand(['get_archive', preprocessed, archive])

    with tarfile.open(archive) as tf:
        assert tf.getnames() == [
            '.', './opt', './opt/archive-file',
        ]
