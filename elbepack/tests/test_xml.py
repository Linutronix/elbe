# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2020 Linutronix GmbH

import contextlib
import io
import pathlib
import subprocess

import pytest

from elbepack.directories import run_elbe_subcommand
from elbepack.tests import parametrize_xml_test_files, xml_test_files


here = pathlib.Path(__file__).parent


@pytest.fixture(scope='module')
def initvm(tmp_path_factory, request):
    if request.config.getoption('--elbe-use-existing-initvm'):
        yield
        return

    initvm_dir = tmp_path_factory.mktemp('initvm-') / 'initvm'

    run_elbe_subcommand(['initvm', 'create', '--fail-on-warning', '--directory', initvm_dir])

    yield

    with contextlib.suppress(Exception):
        run_elbe_subcommand(['initvm', 'destroy', '--directory', initvm_dir])


def _delete_project(uuid):
    with contextlib.suppress(Exception):
        run_elbe_subcommand(['control', 'del_project', uuid])


@pytest.fixture(scope='module', params=xml_test_files('simple'), ids=lambda f: f.name)
def simple_build(request, initvm, tmp_path_factory):
    build_dir = tmp_path_factory.mktemp('build_dir')
    prj = build_dir / 'uuid.prj'

    run_elbe_subcommand([
        'initvm', 'submit', request.param,
        '--output', build_dir,
        '--keep-files', '--build-sdk',
        '--writeproject', prj,
    ])

    uuid = prj.read_text()

    with contextlib.redirect_stdout(io.StringIO()) as stdout:
        run_elbe_subcommand(['control', 'list_projects'])

    if uuid not in stdout.getvalue():
        raise RuntimeError('Project was not created')

    yield build_dir

    _delete_project(uuid)


@pytest.mark.slow
@pytest.mark.parametrize('check_build', ('schema', 'cdrom', 'img', 'sdk', 'rebuild'))
def test_simple_build(simple_build, check_build):
    run_elbe_subcommand(['check-build', check_build, simple_build])


def _prjrepo_list_packages(uuid):
    with contextlib.redirect_stdout(io.StringIO()) as stdout:
        run_elbe_subcommand(['prjrepo', 'list_packages', uuid])

        return stdout.getvalue()


@pytest.mark.slow
@parametrize_xml_test_files('xml', 'pbuilder')
def test_pbuilder_build(initvm, xml, tmp_path, request):
    build_dir = tmp_path
    prj = build_dir / 'uuid.prj'

    run_elbe_subcommand(['pbuilder', 'create', '--xmlfile', xml, '--writeproject', prj])

    uuid = prj.read_text()
    request.addfinalizer(lambda: _delete_project(uuid))

    assert _prjrepo_list_packages(uuid) == ''

    for package in ['libgpio', 'gpiotest']:
        subprocess.run(['git', 'clone', f'https://github.com/Linutronix/{package}.git'],
                       check=True, cwd=build_dir)
        run_elbe_subcommand(['pbuilder', 'build', '--project', uuid,
                             '--source', build_dir.joinpath(package),
                             '--output', build_dir.joinpath('out')])

    assert _prjrepo_list_packages(uuid) == (
        'gpiotest_1.0_amd64.deb\n'
        'libgpio-dev_3.0.0_amd64.deb\n'
        'libgpio1-dbgsym_3.0.0_amd64.deb\n'
        'libgpio1_3.0.0_amd64.deb\n'
    )

    run_elbe_subcommand(['prjrepo', 'upload_pkg', uuid, here / 'equivs-dummy_1.0_all.deb'])

    assert _prjrepo_list_packages(uuid) == (
        'equivs-dummy_1.0_all.deb\n'
        'gpiotest_1.0_amd64.deb\n'
        'libgpio-dev_3.0.0_amd64.deb\n'
        'libgpio1-dbgsym_3.0.0_amd64.deb\n'
        'libgpio1_3.0.0_amd64.deb\n'
    )
