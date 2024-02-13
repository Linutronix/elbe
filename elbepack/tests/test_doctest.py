# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2020 Linutronix GmbH

import doctest

import elbepack.filesystem as filesystem
import elbepack.shellhelper as shellhelper
from elbepack.commands.test import ElbeTestCase


class ElbeDocTest(ElbeTestCase):
    def test_shellhelper(self):
        fail, _ = doctest.testmod(shellhelper)
        self.assertEqual(fail, 0)

    def test_filesystem(self):
        with filesystem.TmpdirFilesystem() as this:
            fail, _ = doctest.testmod(filesystem, extraglobs={'this': this})
        self.assertEqual(fail, 0)
