# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2020-2021 Linutronix GmbH

import os
import sys

from elbepack.commands.test import ElbeTestCase, ElbeTestException, system
from elbepack.directories import elbe_dir, elbe_exe


class TestPreproc(ElbeTestCase):
    def test_preproc(self):
        for param in [os.path.join(elbe_dir, 'tests', fname)
                      for fname
                      in os.listdir(os.path.join(elbe_dir, 'tests'))
                      if fname.startswith('preproc') and fname.endswith('.xml')]:

            with self.subTest(file=param):
                try:
                    system(f'{sys.executable} {elbe_exe} preprocess "{param}"')
                except ElbeTestException as e:
                    self.stdout = e.out
                    raise
