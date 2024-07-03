#!/usr/bin/env python3

"""
Debian and Python have different ways to represent non-release versions.
Compare two version strings respecting these differences.
"""

import re

from debian.debian_support import Version as DebianVersion

from packaging.version import Version as PythonVersion


_deb_pre_re = re.compile(r'^(\w+)(\d+$)')
_deb_pre_to_py_mapping = {
    'alpha': 'a',
    'beta': 'b',
}


def _dep_pre_to_py_pre(deb_pre):
    if deb_pre is None:
        return None

    match = _deb_pre_re.match(deb_pre)
    if match is None:
        raise ValueError(f'Could not match "{deb_pre}"')

    pre = match.group(1)
    num = match.group(2)

    return _deb_pre_to_py_mapping[pre], int(num)


def compare_debian_with_python_version(deb_ver: DebianVersion, py_ver: PythonVersion) -> bool:
    if str(deb_ver) == str(py_ver):
        return True

    if deb_ver.debian_revision is not None or deb_ver.debian_version is not None:
        raise ValueError('Unsupported Debian version components')

    if py_ver.post is not None or py_ver.local is not None:
        raise ValueError('Unsupported Python version components')

    if deb_ver.epoch is None:
        deb_epoch = 0
    else:
        deb_epoch = deb_ver.epoch

    if '~' in deb_ver.upstream_version:
        deb_baseversion, deb_pre = deb_ver.upstream_version.split('~')
    else:
        deb_baseversion, deb_pre = deb_ver.upstream_version, None

    if deb_epoch != py_ver.epoch:
        return False

    if deb_baseversion != py_ver.base_version:
        return False

    if _dep_pre_to_py_pre(deb_pre) != py_ver.pre:
        return False

    return True


def test_compare_debian_with_python_version():
    testcases = [
        ('1.0.0',        '1.0.0',   True),
        ('0.0.1',        '0.0.1',   True),
        ('1.0.0',        '1.0.0a1', False),
        ('1.0.0~alpha1', '1.0.0',   False),
        ('1.0.0~alpha1', '1.0.0a1', True),
        ('1.0.0~alpha1', '1.0.0a2', False),
        ('1.0.0~alpha1', '1.0.0b1', False),
    ]

    for deb_ver, py_ver, result in testcases:
        assert compare_debian_with_python_version(
                DebianVersion(deb_ver),
                PythonVersion(py_ver),
        ) == result


if __name__ == '__main__':
    import argparse
    import sys

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('debian_version', type=DebianVersion, help='Debian version to compare')
    parser.add_argument('python_version', type=PythonVersion, help='Python version to compare')

    args = parser.parse_args()

    sys.exit(not compare_debian_with_python_version(args.debian_version, args.python_version))
