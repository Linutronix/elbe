# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Linutronix GmbH

import os
import subprocess
import sys
import textwrap
import time

from elbepack.cli import CliError, add_argument, with_cli_details
from elbepack.elbexml import ElbeXML, ValidationError
from elbepack.filesystem import TmpdirFilesystem
from elbepack.repodir import Repodir, RepodirError
from elbepack.xmlpreprocess import preprocess_file

prog = os.path.basename(sys.argv[0])


def submit_with_repodir_and_dl_result(control, xmlfile, cdrom, base_image, args):
    fname = f'elbe-repodir-{time.time_ns()}.xml'
    preprocess_xmlfile = os.path.join(os.path.dirname(xmlfile), fname)
    try:
        with Repodir(xmlfile, preprocess_xmlfile):
            _submit_and_dl_result(control, preprocess_xmlfile, cdrom, base_image, args)
    except RepodirError as err:
        raise with_cli_details(err, 127, 'elbe repodir failed')


def _submit_and_dl_result(control, xmlfile, cdrom, base_image, args):

    with preprocess_file(xmlfile, variants=args.variants, sshport=args.sshport,
                         soapport=args.soapport) as xmlfile:

        prjdir = control.service.new_project()
        control.set_xml(prjdir, xmlfile)

    if args.writeproject:
        with open(args.writeproject, 'w') as wpf:
            wpf.write(prjdir)

    if cdrom is not None:
        print('Uploading CDROM. This might take a while')
        control.set_cdrom(prjdir, cdrom)
        print('Upload finished')

    uploaded_base_image_path = None
    if base_image is not None:
        print('Uploading base image. This might take a while')
        uploaded_base_image_path = control.set_base_image(prjdir, base_image)
        print('Upload finished')

    control.service.build(prjdir, args.build_bin, args.build_sources, bool(cdrom),
                          uploaded_base_image_path)

    print('Build started, waiting till it finishes')

    try:
        for msg in control.wait_busy(prjdir):
            print(msg)
    except Exception as e:
        raise with_cli_details(e, 133, textwrap.dedent(f"""
            elbe control wait_busy Failed

            The project will not be deleted.
            The files, that have been built, can be downloaded using:
            {prog} control get_files --output "{args.outdir}" "{prjdir}"

            The project can then be removed using:
            {prog} control del_project "{prjdir}" """))

    print('')
    print('Build finished !')
    print('')

    if args.build_sdk:
        control.service.build_sdk(prjdir)

        print('SDK Build started, waiting till it finishes')

        try:
            for msg in control.wait_busy(prjdir):
                print(msg)
        except Exception:
            print('elbe control wait_busy Failed, while waiting for the SDK',
                  file=sys.stderr)
            print('', file=sys.stderr)
            print('The project will not be deleted.',
                  file=sys.stderr)
            print('The files, that have been built, can be downloaded using:',
                  file=sys.stderr)
            print(
                f'{prog} control get_files --output "{args.outdir}" '
                f'"{prjdir}"',
                file=sys.stderr)
            print('', file=sys.stderr)
            print('The project can then be removed using:',
                  file=sys.stderr)
            print(f'{prog} control del_project "{prjdir}"',
                  file=sys.stderr)
            print('', file=sys.stderr)
            sys.exit(135)

        print('')
        print('SDK Build finished !')
        print('')

    try:
        for chunk in control.dump_file(prjdir, 'validation.txt'):
            sys.stdout.buffer.write(chunk)
        sys.stdout.buffer.flush()
    except Exception:
        print(
            'Project failed to generate validation.txt',
            file=sys.stderr)
        print('Getting log.txt', file=sys.stderr)
        try:
            for chunk in control.dump_file(prjdir, 'log.txt'):
                sys.stdout.buffer.write(chunk)
            sys.stdout.buffer.flush()
        except Exception as e:
            raise with_cli_details(e, 137, textwrap.dedent('Failed to dump log.txt'))
        sys.exit(136)

    if args.skip_download:
        print('')
        print('Listing available files:')
        print('')
        files = control.get_files(prjdir, None)
        for file in files:
            print(f'{file.name}\t{file.description}')

        print('')
        print(f'Get Files with: elbe control get_file "{prjdir}" <filename>')
    else:
        print('')
        print('Getting generated Files')
        print('')

        print(f'Saving generated Files to {args.outdir}')

        for file in control.get_files(prjdir, args.outdir):
            print(f'{file.name}\t{file.description}')

        if not args.keep_files:
            control.service.del_project(prjdir)


def extract_cdrom(cdrom):
    """ Extract cdrom iso image
        returns a TmpdirFilesystem() object containing
        the source.xml, which is also validated.
    """

    tmp = TmpdirFilesystem()
    in_iso_name = 'source.xml'
    try:
        import pycdlib
        iso = pycdlib.PyCdlib()
        iso.open(cdrom)
        extracted = os.path.join(tmp.path, in_iso_name)
        iso.get_file_from_iso(extracted, iso_path=f'/{in_iso_name.upper()};1')
        iso.close()
    except ImportError:
        subprocess.run(['7z', 'x', f'-o{tmp.path}', cdrom, in_iso_name], check=True)

    print('', file=sys.stderr)

    if not tmp.isfile('source.xml'):
        raise CliError(140, textwrap.dedent("""
            Iso image does not contain a source.xml file.
            This is not supported."""))

    try:
        exml = ElbeXML(tmp.fname('source.xml'))
    except ValidationError as e:
        raise with_cli_details(e, 141, textwrap.dedent("""
            Iso image does contain a source.xml file.
            But that xml does not validate correctly."""))

    print('Iso Image with valid source.xml detected !')
    print(f'Image was generated using Elbe Version {exml.get_elbe_version()}')

    return tmp


def add_submit_arguments(f):
    f = add_argument('--skip-download', action='store_true',
                     dest='skip_download', default=False,
                     help='Skip downloading generated Files')(f)

    f = add_argument('--output', dest='outdir',
                     type=os.path.abspath,
                     help='directory where to save downloaded Files')(f)

    f = add_argument('--skip-build-bin', dest='build_bin', action='store_false', default=True,
                     help='Skip building Binary Repository CDROM, for exact Reproduction')(f)

    f = add_argument('--skip-build-sources', action='store_false',
                     dest='build_sources', default=True,
                     help='Skip building Source CDROM')(f)

    f = add_argument('--keep-files', action='store_true',
                     dest='keep_files', default=False,
                     help="don't delete elbe project files after build")(f)

    f = add_argument('--writeproject', dest='writeproject', default=None,
                     help='write project name to file')(f)

    f = add_argument('--build-sdk', dest='build_sdk', action='store_true', default=False,
                     help='Also build an SDK.')(f)

    f = add_argument('--base-image', dest='base_image',
                     help='Use a base image instead of debootstrap (experimental)')(f)

    return f
