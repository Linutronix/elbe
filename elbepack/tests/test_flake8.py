# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2020 Linutronix GmbH

import os

from elbepack.commands.test import ElbeTestCase, system, ElbeTestException
from elbepack.shellhelper import system_out
from elbepack.directories import pack_dir, elbe_exe


class TestPylint(ElbeTestCase):
    global elbe_dir      # pylint: disable=global-statement

    elbe_dir = os.path.join(os.path.dirname(__file__), '../..')

    flake8_opts = ['--max-line-length=100',
                   '--show-source']

    @staticmethod
    def params():
        files = system_out(f"find {pack_dir} -iname '*.py'").splitlines()
        files.append(elbe_exe)
        return files

    def test_lint(self):
        err_out = None
        try:
            system(f"flake8 {' '.join(self.flake8_opts)} {self.param}")
        except ElbeTestException as e:
            err_out = e.out

        if err_out is not None:
            self.fail(err_out)
