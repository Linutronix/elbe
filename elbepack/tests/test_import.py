# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Linutronix GmbH

import importlib
import pkgutil

import pytest

import elbepack

modules = [
    module.name
    for module in pkgutil.walk_packages(elbepack.__path__, elbepack.__name__ + '.')
    if not module.name.endswith('.__main__')
]


@pytest.mark.parametrize('module', modules)
def test_import(module):
    try:
        importlib.import_module(module)
    except ModuleNotFoundError as exc:
        pytest.skip(f'{exc.name} missing')
