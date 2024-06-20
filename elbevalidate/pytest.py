import os
import pathlib
import sys

import pytest


class _MainModule(pytest.Module):
    def _getobj(self):
        return sys.modules['__main__']


class _ElbeValidationPlugin:
    def __init__(self, test_script):
        self.test_script = test_script

    def pytest_addoption(self, parser):
        group = parser.getgroup('elbevalidate')
        group.addoption(
            '--elbe-build-dir',
            dest='elbe_build_dir',
        )

    @staticmethod
    def _elbe_build_dir(config):
        bd = config.option.elbe_build_dir
        if bd is None:
            raise ValueError('--elbe-build-dir was not specified')
        return bd

    @pytest.fixture(name='build_dir')
    def build_dir_fixture(self, request):
        return pathlib.Path(self._elbe_build_dir(request.config))

    def pytest_report_header(self, config):
        bd = self._elbe_build_dir(config)
        return ['elbe build dir: ' + bd]

    def pytest_collect_file(self, file_path, path, parent):
        if os.fspath(file_path) == os.fspath(self.test_script):
            return _MainModule.from_parent(parent, path=file_path)


def run_with_pytest(test_script: os.PathLike, build_dir: os.PathLike):
    """
    Run a Python source file through pytest.

    :param test_script: Script to run.
    :param build_dir: ELBE build directory to validate.
                      Available to tests as fixture `build_dir` of :class:`pathlib.Path`.
    """

    sys.exit(pytest.main(['--elbe-build-dir', os.fspath(build_dir), '--', os.fspath(test_script)],
                         [_ElbeValidationPlugin(test_script)]))
