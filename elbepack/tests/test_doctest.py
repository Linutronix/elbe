# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2020 Linutronix GmbH

import doctest

import elbepack.filesystem as filesystem
import elbepack.shellhelper as shellhelper


def test_shellhelper():
    fail, _ = doctest.testmod(shellhelper)
    assert fail == 0


def test_filesystem():
    with filesystem.TmpdirFilesystem() as this:
        fail, _ = doctest.testmod(filesystem, extraglobs={'this': this})
    assert fail == 0
