# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2020 Linutronix GmbH

import subprocess

import pytest

from elbepack.directories import run_elbe
from elbepack.tests import parametrize_xml_test_files, xml_test_files


@pytest.fixture(scope='module')
def initvm(tmp_path_factory, request):
    if request.config.getoption('--elbe-use-existing-initvm'):
        yield
        return

    initvm_dir = tmp_path_factory.mktemp('initvm-') / 'initvm'

    run_elbe(['initvm', 'create', '--directory', initvm_dir], check=True)

    yield

    run_elbe(['initvm', 'destroy', '--directory', initvm_dir])


def _delete_project(uuid):
    run_elbe(['control', 'del_project', uuid])


@pytest.fixture(scope='module', params=xml_test_files('simple'), ids=lambda f: f.name)
def simple_build(request, initvm, tmp_path_factory):
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
@pytest.mark.parametrize('check_build', ('schema', 'cdrom', 'img', 'sdk', 'rebuild'))
def test_simple_build(simple_build, check_build):
    run_elbe(['check-build', check_build, simple_build], check=True)


@pytest.mark.slow
@parametrize_xml_test_files('xml', 'pbuilder')
def test_pbuilder_build(xml, tmp_path, request):
    build_dir = tmp_path
    prj = build_dir / 'uuid.prj'

    run_elbe(['pbuilder', 'create', '--xmlfile', xml, '--writeproject', prj], check=True)

    uuid = prj.read_text()
    request.addfinalizer(lambda: _delete_project(uuid))

    for package in ['libgpio', 'gpiotest']:
        subprocess.run(['git', 'clone', f'https://github.com/Linutronix/{package}.git'],
                       check=True, cwd=build_dir)
        run_elbe(['pbuilder', 'build', '--project', uuid,
                  '--source', build_dir.joinpath(package), '--output', build_dir.joinpath('out')],
                 check=True)
