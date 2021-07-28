# ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (c) 2020 Olivier Dion <dion@linutronix.de>
#
# SPDX-License-Identifier: GPL-3.0-or-later

import os

from elbepack.commands.test import ElbeTestCase, system, ElbeTestException
from elbepack.shellhelper import system_out
from elbepack.directories import pack_dir, elbe_exe, elbe_dir

class TestPylint(ElbeTestCase):

    pylint_opts = ["--reports=n",
                   "--score=n",
                   "--rcfile=%s" % os.path.join(elbe_dir, ".pylintrc"),
                   "--disable=W0511,R0801"]

    failure_set = {os.path.join(pack_dir, path)
                   for path
                   in [
                       "daemons/soap/esoap.py",

                       # These are not needed to be fixed since
                       # debianize is going to be rewritten
                       "debianize/base/tui.py",
                       "debianize/panels/base.py",
                       "debianize/panels/kernel.py",
                       "debianize/widgets/button.py",
                       "debianize/widgets/edit.py",
                       "debianize/widgets/form.py",
                       "debianize/widgets/grid.py",
                       "debianize/widgets/radio.py",

                       # FIXME: This one is an actual bug to be fixed
                       # 274:30: W0631: Using possibly undefined loop variable 'entry' (undefined-loop-variable)
                       # 276:26: W0631: Using possibly undefined loop variable 'entry' (undefined-loop-variable)
                       "hdimg.py",

                       "initvmaction.py",
                       "log.py",
                       "pbuilderaction.py",
                       "repomanager.py",
                       "rfs.py",
                       "rpcaptcache.py",
                   ]}

    @staticmethod
    def params():
        files = system_out("find %s -iname '*.py'" % pack_dir).splitlines()
        files.append(elbe_exe)
        return files

    def test_lint(self):

        try:
            system("pylint3 %s %s" % (' '.join(self.pylint_opts), self.param))
        except ElbeTestException as e:
            if self.param in TestPylint.failure_set:
                self.stdout = e.out
                self.skipTest("Pylint test for %s is expected to fail" % (self.param))
            else:
                raise
        else:
            if self.param in TestPylint.failure_set:
                raise Exception(f"Pylint test for {self.param} is expected to fail, but did not !")
