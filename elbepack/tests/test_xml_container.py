# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Linutronix GmbH

import os
import pathlib
import shutil
import subprocess

import pytest

from elbepack.buildsubmitaction import extract_cdrom
from elbepack.rootcheck import xml_needs_rootful
from elbepack.tests.test_xml import (  # noqa: F401
    simple_build,
    test_base_extended_build,
    test_check_updates,
    test_rebuild,
    test_simple_build,
)
from elbepack.treeutils import etree

_IMAGE_NAME = 'elbe-buildenv-image'
_REPO_ROOT = pathlib.Path(__file__).parent.parent.parent
_CONTAINERFILE_DIR = _REPO_ROOT / 'contrib' / 'containerfile'
_TESTS_ROOT = _REPO_ROOT / 'tests'


@pytest.fixture(scope='module')
def elbe_buildenv_image():
    subprocess.run(
         ['make', 'build-local', f'BUILD_DIR={_REPO_ROOT}'],
         cwd=_CONTAINERFILE_DIR, check=True)

    return _IMAGE_NAME


def _get_build_container_opts(needs_rootful):
    opts = []

    if os.geteuid() == 0:
        if needs_rootful:
            opts.extend([
                '--cap-add', 'SYS_ADMIN',
                '--cap-add', 'MKNOD',
                '--device-cgroup-rule', 'b *:* rmw',
            ])
        else:
            opts.extend(['--userns', 'auto'])

        opts.extend(['--security-opt', 'apparmor=unconfined'])

        if shutil.which('slirp4netns'):
            opts.extend(['--network', 'slirp4netns'])
        else:
            opts.extend(['--network', 'host'])

    return opts


def _run_build(elbe_buildenv_image, workdir, xml_name, build_args=(), base_image=None,
               source_dir=None):
    """Run ELBE build in container, skipping if loop devices are required but unavailable."""
    input_dir = workdir if source_dir is None else source_dir
    xml_path = input_dir / xml_name

    if xml_name.endswith('.iso'):
        # rebuild-from-iso: extract source.xml for the rootful pre-check, the same
        # way elbe build itself does internally for iso rebuilds.
        extracted = extract_cdrom(xml_path)
        rootcheck_xml = extracted.fname('source.xml')
    else:
        rootcheck_xml = xml_path

    xml = etree(rootcheck_xml)
    needs_rootful = bool(xml_needs_rootful(xml))

    extra_opts = _get_build_container_opts(needs_rootful)

    if needs_rootful and os.geteuid() != 0:
        pytest.skip(
            'XML file requires rootful container. Rerun as root (e.g. `sudo pytest ...`)'
        )

    mounts = []
    if source_dir is None:
        xml_container_path = f'/work/{xml_name}'
    else:
        mounts += ['-v', f'{_TESTS_ROOT.resolve()}:/src:z,ro']
        unresolved_xml_path = xml_path.parent.resolve() / xml_path.name
        xml_container_path = f'/src/{unresolved_xml_path.relative_to(_TESTS_ROOT.resolve())}'

        if xml_path.is_symlink():
            mounts += ['-v', f'{xml_path.resolve()}:{xml_container_path}:z,ro']

    build_cmd = [
        'podman', 'run', '--rm',
        *mounts,
        '-v', f'{workdir}:/work:Z,U',
        *extra_opts,
        elbe_buildenv_image,
        'elbe', 'build', xml_container_path, '--build-dir', '/work/build',
        *build_args,
    ]

    if base_image:
        build_cmd.extend(['--base-image', f'/work/{base_image}'])

    result = subprocess.run(build_cmd, check=False)

    if result.returncode != 0:
        pytest.fail(f'ELBE build failed for {xml_name}. See {workdir} for build state')

    build_dir = workdir / 'build'
    assert (build_dir / 'source.xml').exists()
    assert (build_dir / 'validation.txt').exists()
    return build_dir


@pytest.fixture(scope='module')
def build_driver(elbe_buildenv_image):
    class _ContainerDriver:
        def submit(
            self, request, xml_file, build_dir, *,
            build_sdk=False, skip_cdrom=False, base_image=None,
        ):
            build_args = []
            if skip_cdrom:
                build_args += ['--skip-build-bin', '--skip-build-sources']
            if build_sdk:
                build_args.append('--build-sdk')

            base_image_name = None
            if base_image:
                build_dir.mkdir(parents=True, exist_ok=True)
                shutil.copy(base_image, build_dir)
                base_image_name = base_image.name

            return _run_build(
                elbe_buildenv_image, build_dir, xml_file.name,
                build_args=build_args, base_image=base_image_name,
                source_dir=xml_file.parent,
            )

        def rebuild(self, iso_path, build_dir):
            shutil.copy(iso_path, build_dir)
            _run_build(elbe_buildenv_image, build_dir, iso_path.name,
                       build_args=['--skip-build-sources'])

    return _ContainerDriver()
