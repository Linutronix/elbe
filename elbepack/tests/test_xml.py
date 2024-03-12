# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2020 Linutronix GmbH

import os
import subprocess

from elbepack.directories import elbe_dir, run_elbe

import pytest


def _test_cases(prefix):
    return [
        os.path.join(elbe_dir, 'tests', fname)
        for fname
        in os.listdir(os.path.join(elbe_dir, 'tests'))
        if fname.startswith(prefix) and fname.endswith('.xml')
    ]


def _delete_project(uuid):
    run_elbe(['control', 'del_project', uuid])


@pytest.fixture(scope='module', params=_test_cases('simple'))
def simple_build(request, tmp_path_factory):
    build_dir = tmp_path_factory.mktemp('build_dir')
    prj = build_dir / 'uuid.prj'

    run_elbe([
        'initvm', 'submit', request.param,
        '--output', build_dir,
        '--keep-files', '--build-sdk',
        '--writeproject', prj,
    ], check=True)

    uuid = prj.read_text()

    ps = run_elbe([
        'control', 'list_projects',
    ], capture_output=True, encoding='utf-8', check=True)

    if uuid not in ps.stdout:
        raise RuntimeError('Project was not created')

    yield build_dir

    _delete_project(uuid)


@pytest.mark.slow
@pytest.mark.parametrize('check_build', ('cdrom', 'img', 'sdk', 'rebuild'))
def test_simple_build(simple_build, check_build):
    run_elbe(['check-build', check_build, simple_build], check=True)


@pytest.mark.slow
@pytest.mark.parametrize('xml', _test_cases('pbuilder'))
def test_pbuilder_build(xml, tmp_path, request):
    build_dir = tmp_path
    prj = build_dir / 'uuid.prj'

    run_elbe(['pbuilder', 'create', '--xmlfile', xml, '--writeproject', prj], check=True)

    uuid = prj.read_text()
    request.addfinalizer(lambda: _delete_project(uuid))

    for package in ['libgpio', 'gpiotest']:
        subprocess.run(['git', 'clone', f'https://github.com/Linutronix/{package}.git'],
                       check=True, cwd=build_dir)
        run_elbe(['pbuilder', 'build', '--project', uuid],
                 check=True, cwd=build_dir.joinpath(package))
