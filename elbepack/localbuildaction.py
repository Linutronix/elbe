# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Linutronix GmbH

import os
import shutil
import sys
import textwrap
import time

from elbepack.cli import CliError, with_cli_details
from elbepack.loopcheck import check_loop_mount_requirements
from elbepack.projectmanager import ProjectManager
from elbepack.repodir import Repodir, RepodirError
from elbepack.xmlpreprocess import preprocess_file

prog = os.path.basename(sys.argv[0])


def local_build_with_repodir_and_dl_result(xmlfile, cdrom, base_image, args):
    os.makedirs(args.build_dir, exist_ok=True)
    fname = f'elbe-repodir-{time.time_ns()}.xml'
    preprocess_xmlfile = os.path.join(args.build_dir, fname)
    try:
        with Repodir(xmlfile, preprocess_xmlfile):
            _local_build_and_dl_result(preprocess_xmlfile, cdrom, base_image, args)
    except RepodirError as err:
        raise with_cli_details(err, 127, 'elbe repodir failed')


def _wait_busy(pm, prjdir):
    while True:
        is_busy, msg = pm.project_is_busy(prjdir)

        if msg:
            print(msg)
            continue

        if not is_busy:
            break

        time.sleep(0.1)

    # exited the loop -> the project is not busy anymore,
    # check, whether everything is ok.
    prj = pm.db.get_project_data(prjdir)
    if prj.status != 'build_done':
        raise CliError(191, f'Project build was not successful, current status: {prj.status}')


def _local_build_and_dl_result(xmlfile, cdrom, base_image, args):
    cache_dir = os.path.join(args.build_dir, 'cache')
    pm = ProjectManager(cache_dir)
    try:
        with preprocess_file(xmlfile, variants=args.variants, sshport=args.sshport,
                             soapport=args.soapport) as xmlfile:
            prjdir = pm.create_project(xmlfile)

        if args.writeproject:
            with open(args.writeproject, 'w') as wpf:
                wpf.write(prjdir)

        if cdrom is not None:
            print('Copying CDROM into project. This might take a while')
            shutil.copy(cdrom, os.path.join(prjdir, 'uploaded_cdrom.iso'))
            pm.set_upload_cdrom(prjdir)
            print('Copy finished')

        uploaded_base_image_path = None
        if base_image is not None:
            print('Copying base image into project. This might take a while')
            uploaded_base_image_path = os.path.join(prjdir, 'uploaded_base_image.img')
            shutil.copy(base_image, uploaded_base_image_path)
            print('Copy finished')

        pm.build_project(prjdir, args.build_bin, args.build_sources, bool(cdrom),
                         uploaded_base_image_path, args.exclude_initvm_pkgs)

        print('Build started, waiting till it finishes')

        try:
            _wait_busy(pm, prjdir)
        except Exception as e:
            raise with_cli_details(e, 133, textwrap.dedent(f"""
                Build Failed

                The project will not be deleted.
                Its files are available at:
                {prjdir} """))

        print('')
        print('Build finished !')
        print('')

        if args.build_sdk:
            pm.build_sdk(prjdir, args.exclude_initvm_pkgs)

            print('SDK Build started, waiting till it finishes')

            try:
                _wait_busy(pm, prjdir)
            except Exception:
                print('Waiting for the SDK build Failed', file=sys.stderr)
                print('', file=sys.stderr)
                print('The project will not be deleted.', file=sys.stderr)
                print('Its files are available at:', file=sys.stderr)
                print(prjdir, file=sys.stderr)
                print('', file=sys.stderr)
                sys.exit(135)

            print('')
            print('SDK Build finished !')
            print('')

        try:
            with open(os.path.join(prjdir, 'validation.txt'), 'rb') as f:
                shutil.copyfileobj(f, sys.stdout.buffer)
            sys.stdout.buffer.flush()
        except Exception:
            print(
                'Project failed to generate validation.txt',
                file=sys.stderr)
            print('Getting log.txt', file=sys.stderr)
            try:
                with open(os.path.join(prjdir, 'log.txt'), 'rb') as f:
                    shutil.copyfileobj(f, sys.stdout.buffer)
                sys.stdout.buffer.flush()
            except Exception as e:
                raise with_cli_details(e, 137, textwrap.dedent('Failed to dump log.txt'))
            sys.exit(136)

        files = pm.db.get_project_files(prjdir)

        if args.skip_download:
            print('')
            print('Listing available files:')
            print('')
            for file in files:
                print(f'{file.name}\t{file.description}')

            print('')
            print(f'Files are available at: {prjdir}')
        else:
            print('')
            print('Getting generated Files')
            print('')

            print(f'Saving generated Files to {args.build_dir}')

            os.makedirs(args.build_dir, exist_ok=True)
            for file in files:
                shutil.copy(os.path.join(prjdir, file.name),
                            os.path.join(args.build_dir, os.path.basename(file.name)))
                print(f'{file.name}\t{file.description}')

            if not args.keep_files:
                pm.del_project(prjdir)
    finally:
        pm.stop()
