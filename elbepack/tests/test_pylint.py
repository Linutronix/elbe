# ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (c) 2020 Olivier Dion <dion@linutronix.de>
#
# SPDX-License-Identifier: GPL-3.0-or-later

import os

from elbepack.commands.test import ElbeTestCase
from elbepack.shellhelper import command_out, system_out
from elbepack.directories import elbe_dir

class TestPylint(ElbeTestCase):

    pylint_opts = ["--reports=n",
                   "--score=n",
                   "--rcfile=%s" % os.path.join(elbe_dir, ".pylintrc"),
                   "--disable=W0511,R0801"]

    failure_set = {os.path.join(elbe_dir, path)
                   for path
                   in [
                       "docs/conf.py",
                       "elbepack/daemons/soap/esoap.py",

                       # These are not needed to be fixed since
                       # debianize is going to be rewritten
                       "elbepack/debianize/base/tui.py",
                       "elbepack/debianize/panels/base.py",
                       "elbepack/debianize/panels/kernel.py",
                       "elbepack/debianize/widgets/button.py",
                       "elbepack/debianize/widgets/edit.py",
                       "elbepack/debianize/widgets/form.py",
                       "elbepack/debianize/widgets/grid.py",
                       "elbepack/debianize/widgets/radio.py",

                       "elbepack/elbeproject.py",
                       "elbepack/elbexml.py",

                       # FIXME: This one is an actual bug to be fixed
                       # 274:30: W0631: Using possibly undefined loop variable 'entry' (undefined-loop-variable)
                       # 276:26: W0631: Using possibly undefined loop variable 'entry' (undefined-loop-variable)
                       "elbepack/hdimg.py",

                       "elbepack/initvmaction.py",
                       "elbepack/log.py",
                       "elbepack/pbuilderaction.py",
                       "elbepack/repomanager.py",
                       "elbepack/rfs.py",
                       "elbepack/rpcaptcache.py",
                       "test/updated.py",
                   ]}

    @staticmethod
    def params():
        files = system_out("find %s -iname '*.py'" % elbe_dir).splitlines()
        files.append("elbe")
        return files

    def test_lint(self):

        ret, out = command_out("pylint3 %s %s" % (' '.join(self.pylint_opts), self.param))

        if ret:
            if self.param in TestPylint.failure_set:
                self.skipTest("Pylint test for %s is expected to fail\n%s" % (self.param, out))
            else:
                self.fail(msg=out)
