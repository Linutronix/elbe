import pathlib

import pytest


def _elbe_build_dir(config):
    return config.option.elbe_build_dir


def pytest_addoption(parser):
    group = parser.getgroup('elbevalidate')
    group.addoption(
        '--elbe-build-dir',
        dest='elbe_build_dir',
    )


@pytest.fixture
def build_dir(request):
    bd = _elbe_build_dir(request.config)
    if bd is None:
        raise ValueError('--elbe-build-dir was not specified')
    return pathlib.Path(bd)


def pytest_report_header(config):
    bd = _elbe_build_dir(config)
    if bd is None:
        return
    return ['elbe build dir: ' + bd]
