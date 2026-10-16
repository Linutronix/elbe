# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Linutronix GmbH

import os
import pathlib

import pytest

from elbepack.main import run_elbe_subcommand
from elbepack.tests.elbe_build_command import ElbeBuildCommandDriver
from elbepack.tests.test_xml import XmlBuildTests


class _NativeDriver(ElbeBuildCommandDriver):
    def run_build(self, workdir, xml_file, build_args, base_image, rootful):
        cmd = ['build', str(xml_file), '--build-dir', str(workdir / 'build'), *build_args]
        if base_image:
            cmd.extend(['--base-image', str(workdir / base_image)])

        cwd = pathlib.Path.cwd()
        try:
            run_elbe_subcommand(cmd)
        finally:
            os.chdir(cwd)


@pytest.fixture(scope='module')
def build_driver():
    return _NativeDriver()


class TestNativeBuild(XmlBuildTests):
    pass
