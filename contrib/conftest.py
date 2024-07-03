import pytest


_additional_test_files = {
    'check-deb-py-versions.py',
}


def pytest_collect_file(file_path, parent):
    if file_path.name in _additional_test_files:
        return pytest.Module.from_parent(parent, path=file_path)
