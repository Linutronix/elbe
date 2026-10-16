# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Linutronix GmbH

import pathlib
import subprocess

import pytest

from elbepack.tests.elbe_build_command import ElbeBuildCommandDriver, is_root
from elbepack.tests.test_xml import XmlBuildTests

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

    if is_root():
        if needs_rootful:
            opts.extend([
                '--cap-add', 'SYS_ADMIN',
                '--cap-add', 'MKNOD',
                '--device-cgroup-rule', 'b *:* rmw',
                '--device', '/dev/loop-control',
                '-v', '/dev:/dev',
                '-v', '/run/udev:/run/udev:ro'
            ])
        else:
            opts.extend(['--userns', 'auto'])

        opts.extend(['--network', 'host'])
        opts.extend(['--security-opt', 'apparmor=unconfined'])

    return opts


class _ContainerDriver(ElbeBuildCommandDriver):
    def __init__(self, image):
        self.image = image

    def run_build(self, workdir, xml_file, build_args, base_image, rootful):
        mounts = []
        if xml_file.parent == workdir:
            xml_container_path = f'/work/{xml_file.name}'
        else:
            mounts += ['-v', f'{_TESTS_ROOT.resolve()}:/src:z,ro']
            unresolved_xml_path = xml_file.parent.resolve() / xml_file.name
            xml_container_path = (
                f'/src/{unresolved_xml_path.relative_to(_TESTS_ROOT.resolve())}'
            )

            if xml_file.is_symlink():
                mounts += ['-v', f'{xml_file.resolve()}:{xml_container_path}:z,ro']

        build_cmd = [
            'podman', 'run', '--rm',
            *mounts,
            '-v', f'{workdir}:/work:Z,U',
            *_get_build_container_opts(rootful),
            self.image,
            'elbe', 'build', xml_container_path, '--build-dir', '/work/build',
            *build_args,
        ]

        if base_image:
            build_cmd.extend(['--base-image', f'/work/{base_image}'])

        try:
            subprocess.run(build_cmd, check=True)
        except FileNotFoundError as e:
            raise pytest.fail.Exception(
                f'Cannot run ELBE build for {xml_file.name}: podman is not installed') from e
        except subprocess.CalledProcessError as e:
            raise pytest.fail.Exception(
                f'ELBE build failed for {xml_file.name}. See {workdir} for build state') from e


@pytest.fixture(scope='module')
def build_driver(elbe_buildenv_image):
    return _ContainerDriver(elbe_buildenv_image)


class TestContainerBuild(XmlBuildTests):
    pass
