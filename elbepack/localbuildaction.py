# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Linutronix GmbH

import pathlib
import shutil
import sys
import textwrap
import time

from elbepack.buildsubmitaction import ProjectBackend, build_with_repodir_and_dl_result
from elbepack.cli import CliError
from elbepack.projectmanager import ProjectManager
from elbepack.rootcheck import check_rootful_requirements

prog = pathlib.Path(sys.argv[0]).name


class LocalProjectBackend(ProjectBackend):
    def __init__(self, cache_dir, outdir):
        self.pm = ProjectManager(cache_dir)
        self.outdir = outdir

    def stop(self):
        self.pm.stop()

    def check_preprocessed_xml(self, xmlfile, cdrom):
        check_rootful_requirements(xmlfile, cdrom)

    def create_project(self, xmlfile):
        return self.pm.create_project(xmlfile)

    def set_cdrom(self, prjdir, cdrom):
        shutil.copy(cdrom, pathlib.Path(prjdir) / 'uploaded_cdrom.iso')
        self.pm.set_upload_cdrom(prjdir)

    def set_base_image(self, prjdir, base_image):
        uploaded_base_image_path = pathlib.Path(prjdir) / 'uploaded_base_image.img'
        shutil.copy(base_image, uploaded_base_image_path)
        return uploaded_base_image_path

    def build(self, prjdir, build_bin, build_sources, has_cdrom, uploaded_base_image_path):
        self.pm.build_project(prjdir, build_bin, build_sources, has_cdrom,
                              uploaded_base_image_path, exclude_initvm_pkgs=True)

    def wait_busy(self, prjdir):
        while True:
            is_busy, msg = self.pm.project_is_busy(prjdir)

            if msg:
                yield msg
                continue

            if not is_busy:
                break

            time.sleep(0.1)

        # exited the loop -> the project is not busy anymore,
        # check, whether everything is ok.
        prj = self.pm.db.get_project_data(prjdir)
        if prj.status != 'build_done':
            raise CliError(213, f'Project build was not successful, current status: {prj.status}')

    def build_sdk(self, prjdir):
        self.pm.build_sdk(prjdir, exclude_initvm_pkgs=True)

    def dump_file(self, prjdir, filename, dest):
        with (pathlib.Path(prjdir) / filename).open('rb') as f:
            shutil.copyfileobj(f, dest)

    def get_files(self, prjdir, outdir):
        files = self.pm.db.get_project_files(prjdir)
        if outdir is not None:
            outdir = pathlib.Path(outdir)
            outdir.mkdir(parents=True, exist_ok=True)
        for file in files:
            if outdir is not None:
                shutil.copy(pathlib.Path(prjdir) / file.name,
                            outdir / pathlib.Path(file.name).name)
            yield file

    def del_project(self, prjdir):
        self.pm.del_project(prjdir)

    def recovery_hint(self, prjdir):
        return textwrap.dedent(f"""
            The project will not be deleted.
            Its files are available at:
            {prjdir}""")

    def download_hint(self, prjdir):
        return f'Files are available at: {prjdir}'


def local_build_with_repodir_and_dl_result(xmlfile, cdrom, base_image, args):
    build_dir = pathlib.Path(args.build_dir)
    build_dir.mkdir(parents=True, exist_ok=True)
    backend = LocalProjectBackend(build_dir / 'cache', build_dir)
    try:
        build_with_repodir_and_dl_result(backend, xmlfile, cdrom, base_image, args,
                                         repodir_base=build_dir, xmlfile_base=xmlfile)
    finally:
        backend.stop()
