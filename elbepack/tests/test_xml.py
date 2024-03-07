# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2020 Linutronix GmbH

import os
import sys

from elbepack.commands.test import system
from elbepack.directories import elbe_dir, elbe_exe

import pytest


def _test_cases(prefix):
    return [
        os.path.join(elbe_dir, 'tests', fname)
        for fname
        in os.listdir(os.path.join(elbe_dir, 'tests'))
        if fname.startswith(prefix) and fname.endswith('.xml')
    ]


def _delete_project(uuid):
    system(f'{sys.executable} {elbe_exe} control del_project {uuid}', allow_fail=True)


@pytest.fixture(scope='module', params=_test_cases('simple'))
def simple_build(request, tmp_path_factory):
    build_dir = tmp_path_factory.mktemp('build_dir')
    prj = build_dir / 'uuid.prj'

    system(
        f'{sys.executable} {elbe_exe} initvm submit "{request.param}" '
        f'--output "{build_dir}" --keep-files '
        f'--build-sdk --writeproject "{prj}"')

    uuid = prj.read_text()

    system(f'{sys.executable} {elbe_exe} control list_projects | '
           f'grep {uuid} | grep build_done || false')

    yield uuid

    _delete_project(uuid)


@pytest.mark.slow
@pytest.mark.parametrize('check_build', ('cdrom', 'img', 'sdk', 'rebuild'))
def test_simple_build(simple_build, check_build):
    system(f'{sys.executable} {elbe_exe} check-build {check_build} "{simple_build}"')


@pytest.mark.slow
@pytest.mark.parametrize('xml', _test_cases('pbuilder'))
def test_pbuilder_build(xml, tmp_path, request):
    build_dir = tmp_path
    prj = build_dir / 'uuid.prj'

    system(f'{sys.executable} {elbe_exe} pbuilder create --xmlfile "{xml}" '
           f'--writeproject "{prj}"')

    uuid = prj.read_text()
    request.addfinalizer(lambda: _delete_project(uuid))

    for package in ['libgpio', 'gpiotest']:
        system(f'cd "{build_dir}"; \
                 git clone https://github.com/Linutronix/{package}.git')
        system(f'cd "{build_dir}/{package}"; \
                 {sys.executable} {elbe_exe} pbuilder build --project {uuid}')
