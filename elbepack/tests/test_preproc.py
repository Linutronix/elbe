# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2020-2021 Linutronix GmbH

import os

from elbepack.directories import elbe_dir, run_elbe

import pytest


def _test_cases():
    return [
        os.path.join(elbe_dir, 'tests', fname)
        for fname
        in os.listdir(os.path.join(elbe_dir, 'tests'))
        if fname.startswith('preproc') and fname.endswith('.xml')
    ]


@pytest.mark.parametrize('f', _test_cases())
def test_preproc(f):
    run_elbe(['preprocess', f], check=True)
