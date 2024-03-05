import os
import pytest

import elbepack.directories


def pytest_sessionstart(session):
    elbepack.directories.elbe_exe = os.path.join(os.path.dirname(__file__), 'elbe')
    elbepack.directories.elbe_dir = os.path.dirname(__file__)
