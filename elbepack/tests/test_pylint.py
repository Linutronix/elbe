# ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (c) 2020 Olivier Dion <dion@linutronix.de>
#
# SPDX-License-Identifier: GPL-3.0-or-later

import os
import unittest

from elbepack.shellhelper import system, CommandError

class TestPylint(unittest.TestCase):

    this_dir = os.path.dirname(os.path.realpath(__file__))
    top_dir  = os.path.abspath(os.path.join(this_dir, "..", ".."))
    pylint_opts = ["--reports=n",
                   "--score=n",
                   "--rcfile=%s" % os.path.join(top_dir, ".pylintrc"),
                   "--disable=W0511,R0801",
                   "elbe", "elbepack"]

    def test_lint(self):
        ret = True
        try:
            system("pylint %s" % " ".join(self.pylint_opts))
        except CommandError as E:
            print(E)
            ret = False

        self.assertTrue(ret)
