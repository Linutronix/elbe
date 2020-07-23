# ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (c) 2020 Olivier Dion <dion@linutronix.de>
#
# SPDX-License-Identifier: GPL-3.0-or-later

import doctest

import elbepack.shellhelper as shellhelper
import elbepack.filesystem as filesystem

from elbepack.commands.test import ElbeTestCase

class ElbeDocTest(ElbeTestCase):

    # This is an example of a callable parametrization
    @staticmethod
    def params():
        return [shellhelper, filesystem]

    def setUp(self):

        self.kwargs = {}

        if self.param is filesystem:
            self.kwargs["extraglobs"] = {"this":filesystem.TmpdirFilesystem()}

    def tearDown(self):

        if self.param is filesystem:
            self.kwargs["extraglobs"]["this"].delete()

    def test_doctest(self):
        fail, _ = doctest.testmod(self.param, **self.kwargs)
        self.assertEqual(fail, 0)
