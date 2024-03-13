# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2020 Linutronix GmbH

import subprocess


def test_flake8():
    subprocess.run([
        'flake8',
        '--max-line-length=100', '--show-source',
        'elbepack',
    ], check=True)
