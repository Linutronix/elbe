# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2024 Linutronix GmbH

import os
import subprocess
import tempfile
from pathlib import Path

import pytest


# https://stackoverflow.com/a/61193490
def pytest_addoption(parser):
    parser.addoption(
        '--runslow', action='store_true', default=False, help='run slow tests'
    )
    parser.addoption(
        '--elbe-use-initvm', action='store', default='libvirt',
        choices=('libvirt', 'qemu', 'existing'),
        help='use specific initvm',
    )


def _is_ram_backed(path):
    fstype = subprocess.run(
        ['stat', '-f', '-c', '%T', path],
        capture_output=True, text=True, check=False,
    ).stdout.strip()
    return fstype in ('tmpfs', 'ramfs')


def pytest_configure(config):
    config.addinivalue_line('markers', 'slow: mark test as slow to run')

    # spyne's SixMetaPathImporter is appended to sys.meta_path and thus
    # related warnings be repeatedly triggered by subsequent imports
    # For pytest that can only realiably be suppressed by explicitly adding
    # it to it's warnings filter context manager.
    config.addinivalue_line(
        'filterwarnings', 'ignore:_SixMetaPathImporter:ImportWarning',
    )

    # Make sure the setting is also propagated through run_elbe.
    warnings = config.getini('filterwarnings')
    if warnings:
        os.environ.setdefault('PYTHONWARNINGS', ' '.join(warnings))

    # Avoid filling up the RAM with large build artifacts: unless the user
    # chose a location, move away from the default temp dir if it is RAM-backed.
    if 'TMPDIR' not in os.environ and not config.option.basetemp:
        if _is_ram_backed(Path(tempfile.gettempdir())):
            var_tmp = Path('/var/tmp')
            if not var_tmp.is_dir() or not os.access(var_tmp, os.W_OK | os.X_OK):
                raise pytest.UsageError(
                    f'{tempfile.gettempdir()} is RAM-backed and {var_tmp} is not a'
                    ' writable directory. Large build artifacts would fill up the'
                    ' RAM. Use --basetemp=<dir> or set TMPDIR to select another'
                    ' location.',
                )
            os.environ['TMPDIR'] = str(var_tmp)
            # tempfile has cached the old location by now, so reset
            tempfile.tempdir = None


def pytest_collection_modifyitems(config, items):
    if config.getoption('--runslow'):
        # --runslow given in cli: do not skip slow tests
        return
    skip_slow = pytest.mark.skip(reason='need --runslow option to run')
    for item in items:
        if 'slow' in item.keywords:
            item.add_marker(skip_slow)
