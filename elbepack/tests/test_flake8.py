# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2020 Linutronix GmbH

import glob
import subprocess

from elbepack.directories import elbe_exe, pack_dir

import pytest


def _python_files():
    files = glob.glob(pack_dir + '/**/*.py', recursive=True)
    files.append(elbe_exe)
    return files


@pytest.mark.parametrize('f', _python_files())
def test_flake8(f):
    subprocess.run(['flake8', '--max-line-length=100', '--show-source', f], check=True)
