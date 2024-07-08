# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2024 Linutronix GmbH

import pathlib

import pytest


def xml_test_files(prefix):
    return [
        file
        for file
        in pathlib.Path('tests').iterdir()
        if file.name.startswith(prefix) and file.name.endswith('.xml')
    ]


def parametrize_xml_test_files(name, prefix):
    """ Decorator to parametrize test functions for matching test XML files """

    files = xml_test_files(prefix)

    def wrapper(func):
        return pytest.mark.parametrize(
                name, files,
                ids=[file.name for file in files]
        )(func)

    return wrapper
