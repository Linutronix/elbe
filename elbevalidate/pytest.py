# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2024 Linutronix GmbH

import importlib
import os
import sys

import pytest

# Don't import the plugin here as pytest will perform some import-time hooks
plugin = importlib.util.resolve_name('.._pytest_plugin', __name__)


class _MainModule(pytest.Module):
    def _getobj(self):
        return sys.modules['__main__']


class _ElbeValidationPlugin:
    def __init__(self, test_script):
        self.test_script = test_script

    def pytest_collect_file(self, file_path, parent):
        if not file_path.suffix == '.py' and os.fspath(file_path) == os.fspath(self.test_script):
            return _MainModule.from_parent(parent, path=file_path)

    @pytest.hookimpl
    def pytest_cmdline_parse(self, pluginmanager, args):
        # May already have been registered through conftest.py
        if not pluginmanager.has_plugin(plugin):
            pluginmanager.register(pluginmanager.import_plugin(plugin))


def run_with_pytest(test_script: os.PathLike, build_dir: os.PathLike):
    """
    Run a Python source file through pytest.

    :param test_script: Script to run.
    :param build_dir: ELBE build directory to validate.
                      Available to tests as fixture `build_dir` of :class:`pathlib.Path`.
    """

    sys.exit(pytest.main(['--elbe-build-dir', os.fspath(build_dir), '--', os.fspath(test_script)],
                         [_ElbeValidationPlugin(test_script)]))
