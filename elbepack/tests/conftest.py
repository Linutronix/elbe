# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Linutronix GmbH

import datetime
import os
import pathlib
import shutil
import subprocess
import tempfile
from typing import List, Optional

import pytest

from elbepack.tests.test_helpers import elbevalidate  # noqa: F401

_WORKDIR_RETENTION = 3


def _elbe_test_workdir_root() -> pathlib.Path:
    root = pathlib.Path('/var/tmp/elbe-tests')
    root.mkdir(parents=True, exist_ok=True)
    return root


def _prune_old_workdirs(root: pathlib.Path, keep: int = _WORKDIR_RETENTION):
    dirs = sorted((p for p in root.iterdir() if p.is_dir()),
                  key=lambda p: p.stat().st_mtime, reverse=True)
    for stale in dirs[keep:]:
        shutil.rmtree(stale, ignore_errors=True)


def _mk_workdir(root: pathlib.Path, prefix: str) -> pathlib.Path:
    timestamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H%M%SZ')
    return pathlib.Path(tempfile.mkdtemp(prefix=f'{prefix}-{timestamp}-', dir=root))


class ElbePodmanContainer:
    def __init__(self):
        self.container_id = None
        self.image_name = 'elbe-buildenv-image'
        self.build_dir = None
        self.cache_dir = None
        self.containerfile_dir = (pathlib.Path(__file__).parent.parent.parent /
                                  'contrib' / 'containerfile-vmless')

    def build_image(self):
        print(f'[CONTAINER] Building container image from {self.containerfile_dir}')

        original_cwd = os.getcwd()
        try:
            os.chdir(self.containerfile_dir)
            print(f'[CONTAINER] Running: make build-local BUILD_DIR={original_cwd}')

            result = subprocess.run([
                'make', 'build-local',
                f'BUILD_DIR={original_cwd}'
            ], text=True)

            if result.returncode != 0:
                msg = f'Container image build failed with return code {result.returncode}'
                raise RuntimeError(msg)

            print(f'[CONTAINER] Image built successfully: {self.image_name}')

        except subprocess.CalledProcessError as e:
            print(f'[CONTAINER] Build failed: {e}')
            print(f'[CONTAINER] stdout: {e.stdout}')
            print(f'[CONTAINER] stderr: {e.stderr}')
            raise
        except Exception as e:
            print(f'[CONTAINER] Unexpected error during build: {e}')
            raise
        finally:
            os.chdir(original_cwd)

    def start_container(self, build_dir: pathlib.Path,
                        cache_dir: pathlib.Path,
                        input_dir: Optional[pathlib.Path] = None,
                        base_image_dir: Optional[pathlib.Path] = None):
        self.build_dir = build_dir
        self.cache_dir = cache_dir

        build_dir.mkdir(parents=True, exist_ok=True)
        cache_dir.mkdir(parents=True, exist_ok=True)

        cmd = [
            'podman', 'run', '-d',
            '--rm',
            '--cap-add', 'CAP_SYS_ADMIN',
            '--device', '/dev/fuse',
            '-v', f'{build_dir}:/build:Z',
            '-v', f'{cache_dir}:/var/cache/elbe:Z',
        ]

        if input_dir:
            cmd.extend(['-v', f'{input_dir}:/input:Z'])

        if base_image_dir:
            cmd.extend(['-v', f'{base_image_dir}:/base-image:Z'])

        cmd.extend([
            '--name', 'elbe-test-container',
            self.image_name,
            '/bin/sh', '-c', 'sleep 3600'
        ])

        print(f'[CONTAINER] Starting container with command: {" ".join(cmd)}')

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f'Failed to start container: {result.stderr}')

        self.container_id = result.stdout.strip()
        print(f'Started container {self.container_id}')

    def run_command(self, cmd: List[str], working_dir: Optional[str] = None,
                    capture_output: bool = True) -> subprocess.CompletedProcess:
        if not self.container_id:
            raise RuntimeError('Container not started')

        podman_cmd = ['podman', 'exec']
        if working_dir:
            podman_cmd.extend(['-w', working_dir])
        podman_cmd.extend([self.container_id] + cmd)

        print(f'[CONTAINER] Running: {" ".join(podman_cmd)}')

        if capture_output:
            return subprocess.run(podman_cmd, capture_output=True, text=True,
                                  check=False)
        else:
            return subprocess.run(podman_cmd, text=True, check=False)

    def run_elbe_command(self, args: List[str],
                         capture_output: bool = True) -> subprocess.CompletedProcess:
        return self.run_command(['elbe'] + args, working_dir='/build',
                                capture_output=capture_output)

    def cleanup(self):
        if self.container_id:
            try:
                subprocess.run(['podman', 'stop', self.container_id],
                               capture_output=True, check=False)
                subprocess.run(['podman', 'rm', self.container_id],
                               capture_output=True, check=False)
                print(f'Cleaned up container {self.container_id}')
            except Exception as e:
                print(f'Error cleaning up container: {e}')
            finally:
                self.container_id = None


@pytest.fixture(scope='session')
def elbepack_repo_root() -> pathlib.Path:
    return pathlib.Path(__file__).parent.parent.parent


@pytest.fixture(scope='session')
def elbe_podman_container(elbepack_repo_root: pathlib.Path):
    container = ElbePodmanContainer()

    print("[CONTAINER] Building container image to ensure it's up-to-date...")
    container.build_image()

    yield container

    container.cleanup()


@pytest.fixture(scope='session')
def elbe_test_workdir_root() -> pathlib.Path:
    root = _elbe_test_workdir_root()
    _prune_old_workdirs(root)
    print(f'[CONTAINER] Intermediate artifacts and logs are kept at {root}')
    return root


@pytest.fixture
def elbe_test_workdir(elbe_test_workdir_root: pathlib.Path) -> pathlib.Path:
    return _mk_workdir(elbe_test_workdir_root, 'build')


@pytest.fixture(scope='module')
def elbe_base_image_workdir(elbe_test_workdir_root: pathlib.Path) -> pathlib.Path:
    return _mk_workdir(elbe_test_workdir_root, 'base_image_build')
