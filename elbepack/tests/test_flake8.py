# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2020 Linutronix GmbH

from elbepack.commands.test import ElbeTestCase, ElbeTestException, system
from elbepack.directories import elbe_exe, pack_dir
from elbepack.shellhelper import system_out


class TestPylint(ElbeTestCase):
    flake8_opts = ['--max-line-length=100',
                   '--show-source']

    def test_lint(self):
        files = system_out(f"find {pack_dir} -iname '*.py'").splitlines()
        files.append(elbe_exe)

        for f in files:
            with self.subTest(file=f):
                err_out = None
                try:
                    system(f"flake8 {' '.join(self.flake8_opts)} {f}")
                except ElbeTestException as e:
                    err_out = e.out

                if err_out is not None:
                    self.fail(err_out)
