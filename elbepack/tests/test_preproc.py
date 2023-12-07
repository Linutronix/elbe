# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2020-2021 Linutronix GmbH

import os
import sys

from elbepack.commands.test import ElbeTestCase, system, ElbeTestException
from elbepack.directories import elbe_exe, elbe_dir


class TestPreproc(ElbeTestCase):
    global elbe_dir

    elbe_dir = os.path.join(os.path.dirname(__file__), '../..')

    failure_set = {os.path.join(elbe_dir, path)
                   for path
                   in [
                       'tests/preproc-01.xml'
                   ]}

    params = [os.path.join(elbe_dir, 'tests', fname)
              for fname
              in os.listdir(os.path.join(elbe_dir, 'tests'))
              if fname.startswith('preproc') and fname.endswith('.xml')]

    def test_preproc(self):

        try:
            system(f'{sys.executable} {elbe_exe} preprocess "{self.param}"')
        except ElbeTestException as e:
            if self.param in TestPreproc.failure_set:
                self.stdout = e.out
                self.skipTest(
                    f'Preproc test for {self.param} is expected to fail')
            else:
                raise
        else:
            if self.param in TestPreproc.failure_set:
                raise Exception(f'Preproc test for {self.param}'
                      'is expected to fail, but did not !')
