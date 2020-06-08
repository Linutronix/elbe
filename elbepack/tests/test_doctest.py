# ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (c) 2020 Olivier Dion <dion@linutronix.de>
#
# SPDX-License-Identifier: GPL-3.0-or-later

import doctest
import unittest

import elbepack.shellhelper as shellhelper
import elbepack.filesystem as filesystem

from elbepack.commands.test import ElbeTestCase

class ElbeDocTest(ElbeTestCase):

    params = [shellhelper, filesystem]

    def setUp(self):

        self.kwargs = {}

        if self.params is filesystem:
            self.kwargs["extraglobs"] = {"this":filesystem.TmpdirFilesystem()}

    def tearDown(self):

        if self.params is filesystem:
            self.kwargs["extraglobs"]["this"].delete()

    def test_doctest(self):
        fail, _ = doctest.testmod(self.params, **self.kwargs)
        self.assertEqual(fail, 0)
