# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2020 Linutronix GmbH


# Only contains templates used by other test files
__test__ = False

import pathlib

import pytest

from elbepack.main import run_elbe_subcommand
from elbepack.tests import xml_test_files


CHECK_BUILD_VARIANTS = ('schema', 'cdrom', 'img', 'sdk')

_EXTENDED_XML = (
    pathlib.Path('tests') / 'base-extended' / 'simple-validation' / 'image-extended.xml'
)


@pytest.fixture(scope='module', params=xml_test_files('simple'), ids=lambda f: f.name)
def simple_build(request, tmp_path_factory, build_driver):
    workdir = tmp_path_factory.mktemp('build_dir')
    return build_driver.submit(request, request.param, workdir, build_sdk=True)


@pytest.mark.slow
@pytest.mark.parametrize('check_build', CHECK_BUILD_VARIANTS)
def test_simple_build(simple_build, check_build):
    run_elbe_subcommand(['check-build', check_build, simple_build])


@pytest.mark.slow
def test_rebuild(build_driver, simple_build, tmp_path_factory):
    build_dir = tmp_path_factory.mktemp('build_dir')
    build_driver.rebuild(simple_build / 'bin-cdrom.iso', build_dir)


@pytest.mark.slow
def test_check_updates(simple_build):
    run_elbe_subcommand(['check_updates', simple_build / 'source.xml'])


@pytest.mark.slow
def test_base_extended_build(request, build_driver, simple_build, tmp_path):
    base_build_image = simple_build / 'base-rootfs.tgz'

    if not base_build_image.exists():
        pytest.skip('No base image tarball was produced')

    extended_build = tmp_path / 'extended-build'
    extended_build.mkdir()
    build_dir = build_driver.submit(
        request, _EXTENDED_XML, extended_build,
        skip_cdrom=True, base_image=base_build_image,
    )
    run_elbe_subcommand(['check-build', 'img', build_dir])
