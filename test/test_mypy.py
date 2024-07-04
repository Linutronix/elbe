import importlib

import pytest


@pytest.fixture
def mypy_api():
    try:
        return importlib.import_module('mypy.api', package=__name__)
    except ModuleNotFoundError as e:
        if e.name == 'mypy':
            pytest.skip(f'module {e.name} not found')
        else:
            raise


def test_mypy(mypy_api):
    normal_report, error_report, exit_status = mypy_api.run([])
    if exit_status:
        pytest.fail(normal_report, error_report)
