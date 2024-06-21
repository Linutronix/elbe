import os

import pytest


# https://stackoverflow.com/a/61193490
def pytest_addoption(parser):
    parser.addoption(
        '--runslow', action='store_true', default=False, help='run slow tests'
    )
    parser.addoption(
        '--elbe-use-existing-initvm', action='store_true', default=False,
        help='reuse existing elbe initvm',
    )


def pytest_configure(config):
    config.addinivalue_line('markers', 'slow: mark test as slow to run')

    # Make sure the setting is also propagated through run_elbe.
    warnings = config.getini('filterwarnings')
    if warnings:
        os.environ.setdefault('PYTHONWARNINGS', ' '.join(warnings))


def pytest_collection_modifyitems(config, items):
    if config.getoption('--runslow'):
        # --runslow given in cli: do not skip slow tests
        return
    skip_slow = pytest.mark.skip(reason='need --runslow option to run')
    for item in items:
        if 'slow' in item.keywords:
            item.add_marker(skip_slow)
