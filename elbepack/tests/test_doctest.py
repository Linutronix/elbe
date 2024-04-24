# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2020 Linutronix GmbH

import doctest

import pytest

import elbepack.aptpkgutils as aptpkgutils
import elbepack.filesystem as filesystem
import elbepack.shellhelper as shellhelper


@pytest.mark.parametrize('mod', [shellhelper, aptpkgutils])
def test(mod):
    fail, _ = doctest.testmod(mod)
    assert fail == 0


def test_filesystem():
    with filesystem.TmpdirFilesystem() as this:
        fail, _ = doctest.testmod(filesystem, extraglobs={'this': this})
    assert fail == 0
