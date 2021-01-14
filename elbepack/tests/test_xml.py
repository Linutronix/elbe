# ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (c) 2020 Olivier Dion <dion@linutronix.de>
#
# SPDX-License-Identifier: GPL-3.0-or-later

import os
import unittest
import tempfile

from elbepack.directories import elbe_dir, elbe_exe
from elbepack.commands.test import ElbeTestCase, ElbeTestLevel
from elbepack.shellhelper import command_out

def system(cmd, allow_fail=False):
    ret, out = command_out(cmd)
    if ret != 0 and not allow_fail:
        raise Exception(out)

@unittest.skipIf(ElbeTestCase.level < ElbeTestLevel.INITVM,
                 "Test level not set to INITVM")
class TestSimpleXML(ElbeTestCase):

    params = [os.path.join(elbe_dir, "tests", fname)
              for fname
              in os.listdir(os.path.join(elbe_dir, "tests"))
              if fname.startswith("simple") and fname.endswith(".xml")]

    def test_simple_build(self):

        with tempfile.TemporaryDirectory(prefix="elbe-test-simple-xml-") as build_dir:

            prj  = os.path.join(build_dir, "uuid.prj")
            uuid = None

            try:
                system('%s initvm submit "%s" --output "%s" --keep-files '
                       '--build-sdk --writeproject "%s"' %
                       (elbe_exe, self.param, build_dir, prj))

                # Ensure project build is done
                with open(prj, "r") as f:
                    uuid = f.read()
                    system("%s control list_projects | "
                           "grep %s | grep build_done || false" %
                           (elbe_exe, uuid))

                for cmd in ("cdrom", "img", "sdk", "rebuild"):
                    with self.subTest(f'check build {cmd}'):
                        system('%s check-build %s "%s"' % (elbe_exe, cmd, build_dir))

            # pylint: disable=try-except-raise
            except:
                raise
            else:
                # This is a tear down of the project, it's okay if it fails
                system('%s control del_project %s' % (elbe_exe, uuid),
                       allow_fail=True)

@unittest.skipIf(ElbeTestCase.level < ElbeTestLevel.INITVM,
                 "Test level not set to INITVM")
class TestPbuilder(ElbeTestCase):

    params = [os.path.join(elbe_dir, "tests", fname)
              for fname
              in os.listdir(os.path.join(elbe_dir, "tests"))
              if fname.startswith("pbuilder") and fname.endswith(".xml")]

    def test_pbuilder_build(self):

        with tempfile.TemporaryDirectory(prefix="elbe-test-pbuilder-xml-") as build_dir:

            prj  = os.path.join(build_dir, "uuid.prj")
            uuid = None

            try:
                system('%s pbuilder create --xmlfile "%s" --writeproject "%s"' %
                       (elbe_exe, self.param, prj))

                with open(prj, "r") as f:
                    uuid = f.read()
                    system('cd "%s"; %s pbuilder build --project %s' % (build_dir,
                                                                        elbe_exe,
                                                                        uuid))
            # pylint: disable=try-except-raise
            except:
                raise
            else:
                # This is a tearDown of the project, it's okay if it fails
                system('%s control del_project %s' % (elbe_exe, uuid),
                       allow_fail=True)
