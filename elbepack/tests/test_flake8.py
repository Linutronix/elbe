# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2020 Linutronix GmbH

import glob

from elbepack.commands.test import ElbeTestException, system
from elbepack.directories import elbe_exe, pack_dir

import pytest


flake8_opts = ['--max-line-length=100',
               '--show-source']


def _python_files():
    files = glob.glob(pack_dir + '/**/*.py', recursive=True)
    files.append(elbe_exe)
    return files


@pytest.mark.parametrize('f', _python_files())
def test_flake8(f):
    try:
        system(f'flake8 {" ".join(flake8_opts)} {f}')
    except ElbeTestException as e:
        pytest.fail(e.out)
