# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Linutronix GmbH

import os
import shutil

import pytest

from elbepack.buildsubmitaction import extract_cdrom
from elbepack.rootcheck import xml_needs_rootful
from elbepack.treeutils import etree


def needs_rootful(xml_path):
    if xml_path.suffix == '.iso':
        # rebuild-from-iso: extract source.xml for the rootful pre-check, the same
        # way elbe build itself does internally for iso rebuilds.
        with extract_cdrom(xml_path) as tmp:
            return bool(xml_needs_rootful(etree(tmp.fname('source.xml'))))

    return bool(xml_needs_rootful(etree(xml_path)))


def is_root():
    return os.geteuid() == 0


class ElbeBuildCommandDriver:
    def run_build(self, workdir, xml_file, build_args, base_image, rootful):
        raise NotImplementedError

    def _build(self, workdir, xml_file, build_args, base_image=None):
        rootful = needs_rootful(xml_file)
        if rootful and not is_root():
            pytest.skip(
                'XML file requires root privileges. Rerun as root (e.g. `sudo pytest ...`)'
            )

        self.run_build(workdir, xml_file, build_args, base_image, rootful)

        build_dir = workdir / 'build'
        assert (build_dir / 'source.xml').exists()
        assert (build_dir / 'validation.txt').exists()
        return build_dir

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

        return self._build(build_dir, xml_file, build_args, base_image_name)

    def rebuild(self, iso_path, build_dir):
        shutil.copy(iso_path, build_dir)
        self._build(build_dir, build_dir / iso_path.name, ['--skip-build-sources'])
