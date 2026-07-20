# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Linutronix GmbH

import pathlib
import socket

import pytest


def _free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


def _run_build_test(workdir, elbe_podman_container, xml_file, test_name, base_image_path=None):
    port = _free_port()
    build_dir = workdir / 'build'
    cache_dir = workdir / 'cache'
    input_dir = xml_file.parent

    base_image_dir = base_image_path.parent if base_image_path else None
    elbe_podman_container.start_container(build_dir, cache_dir, input_dir,
                                          base_image_dir=base_image_dir)
    print(f'[TEST] Container started for {test_name}, '
          f'build_dir: {build_dir}, cache_dir: {cache_dir}')

    try:
        cmd = [
            'build',
            '--host', '127.0.0.1',
            '--port', str(port),
            '--output', '/build/build',
            '/input/' + xml_file.name,
        ]

        if base_image_path is not None:
            base_image_name = base_image_path.name
            cmd.extend(['--base-image', f'/base-image/{base_image_name}'])

        result = elbe_podman_container.run_elbe_command(cmd, capture_output=False)

        if result.returncode != 0:
            msg = (
                f'ELBE build failed for {test_name} in container. '
                f'See {cache_dir} for the log file and other build state'
            )
            pytest.fail(msg)

        build_output = build_dir / 'build'
        print(f'[TEST] Checking for {test_name} output files in {build_output}')
        files = (list(build_output.iterdir()) if build_output.exists()
                 else 'Build dir does not exist')
        print(f'[TEST] Files in build dir: {files}')

        assert build_dir.joinpath('build', 'source.xml').exists()
        assert build_dir.joinpath('build', 'validation.txt').exists()

        return build_dir
    finally:
        elbe_podman_container.cleanup()


@pytest.fixture(scope='module')
def base_image_path(elbe_base_image_workdir, elbe_podman_container):
    base_xml = (
        pathlib.Path(__file__).parent.parent.parent / 'tests' / 'base-extended'
        / 'simple-validation' / 'image-base-trixie.xml'
    )

    build_dir = _run_build_test(elbe_base_image_workdir, elbe_podman_container,
                                base_xml, 'base image (fixture)')
    base_image_path = build_dir / 'build' / 'base-rootfs.tgz'

    if not base_image_path.exists():
        pytest.fail('Base image not found after build')

    return base_image_path


@pytest.mark.slow
def test_build_base_image(base_image_path):
    assert base_image_path.exists()


@pytest.mark.slow
def test_build_extended_image(
        elbe_test_workdir, elbe_podman_container, base_image_path):
    extended_xml = (
        pathlib.Path(__file__).parent.parent.parent / 'tests' / 'base-extended'
        / 'simple-validation' / 'image-extended-trixie.xml'
    )

    _run_build_test(
        elbe_test_workdir, elbe_podman_container, extended_xml,
        'extended image', base_image_path=base_image_path
    )
