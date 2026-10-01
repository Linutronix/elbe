# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2020 Linutronix GmbH

import contextlib
import functools
import io
import pathlib
import subprocess

import pytest

from elbepack.main import run_elbe_subcommand
from elbepack.tests import parametrize_xml_test_files
from elbepack.tests.test_xml import (  # noqa: F401
    simple_build,
    test_base_extended_build,
    test_check_updates,
    test_rebuild,
    test_simple_build,
)


here = pathlib.Path(__file__).parent


@pytest.fixture(scope='module')
def initvm(tmp_path_factory, request):
    initvm_dir = tmp_path_factory.mktemp('initvm-') / 'initvm'
    use_initvm = request.config.getoption('--elbe-use-initvm')

    if use_initvm in {'libvirt', 'existing'}:
        qemu_arg = []
    elif use_initvm == 'qemu':
        qemu_arg = ['--qemu']
    else:
        raise ValueError(use_initvm)

    def initvm_func(subcmd, *args):
        run_elbe_subcommand(['initvm', subcmd, '--directory', initvm_dir, *qemu_arg, *args])

    def destroy_initvm():
        with contextlib.suppress(Exception):
            initvm_func('stop')
        with contextlib.suppress(Exception):
            initvm_func('destroy')

    if use_initvm == 'existing':
        yield initvm_func
        return

    try:
        initvm_func('create', '--fail-on-warning')
    except Exception as e:
        # If the fixture setup fails, pytest will try to create the fixture for
        # each test. This is very slow and unlikely to work, so remember the failure.
        def error_func(*args, _initvm_exception, **kwargs):
            raise RuntimeError('initvm setup failed') from _initvm_exception
        destroy_initvm()
        yield functools.partial(error_func, _initvm_exception=e)
    else:
        try:
            yield initvm_func
        finally:
            destroy_initvm()


def _delete_project(uuid):
    with contextlib.suppress(Exception):
        run_elbe_subcommand(['control', 'del_project', uuid])


@pytest.fixture(scope='module')
def build_driver(initvm):
    class _InitvmDriver:
        def submit(
            self, request, xml_file, build_dir, *,
            build_sdk=False, skip_cdrom=False, base_image=None,
        ):
            prj = build_dir / 'uuid.prj'

            args = ['submit', xml_file, '--output', build_dir,
                    '--keep-files', '--writeproject', prj]
            if build_sdk:
                args.append('--build-sdk')
            if skip_cdrom:
                args += ['--skip-build-bin', '--skip-build-sources']
            if base_image:
                args += ['--base-image', base_image]

            initvm(*args)

            uuid = prj.read_text()

            with contextlib.redirect_stdout(io.StringIO()) as stdout:
                run_elbe_subcommand(['control', 'list_projects'])

            if uuid not in stdout.getvalue():
                raise RuntimeError('Project was not created')

            request.addfinalizer(lambda: _delete_project(uuid))

            return build_dir

        def rebuild(self, iso_path, build_dir):
            initvm(
                'submit', '--skip-build-source',
                '--output', build_dir,
                iso_path,
            )

    return _InitvmDriver()


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

    # Not necessary, to test the command.
    run_elbe_subcommand(['pbuilder', 'update', '--project', uuid])
    run_elbe_subcommand(['control', 'wait_busy', uuid])

    assert _prjrepo_list_packages(uuid) == ''

    for package in ['libgpio', 'gpiotest']:
        subprocess.run(['git', 'clone', f'https://github.com/Linutronix/{package}.git'],
                       check=True, cwd=build_dir)
        run_elbe_subcommand(['pbuilder', 'build', '--project', uuid,
                             '--source', build_dir.joinpath(package),
                             '--output', build_dir.joinpath('out')])

    assert _prjrepo_list_packages(uuid) == (
        'gpiotest_1.0_amd64.deb\n'
        'libgpio-dev_3.0.1_amd64.deb\n'
        'libgpio3-dbgsym_3.0.1_amd64.deb\n'
        'libgpio3_3.0.1_amd64.deb\n'
    )

    run_elbe_subcommand(['prjrepo', 'upload_pkg', uuid, here / 'equivs-dummy_1.0_all.deb'])

    assert _prjrepo_list_packages(uuid) == (
        'equivs-dummy_1.0_all.deb\n'
        'gpiotest_1.0_amd64.deb\n'
        'libgpio-dev_3.0.1_amd64.deb\n'
        'libgpio3-dbgsym_3.0.1_amd64.deb\n'
        'libgpio3_3.0.1_amd64.deb\n'
    )
