# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Linutronix GmbH

import abc
import argparse
import os
import pathlib
import subprocess
import sys
import textwrap
import time

from elbepack.cli import CliError, add_argument, with_cli_details
from elbepack.elbexml import ElbeXML, ValidationError
from elbepack.filesystem import TmpdirFilesystem
from elbepack.repodir import Repodir, RepodirError
from elbepack.xmlpreprocess import preprocess_file


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


def xml_or_iso_file(value):
    if not value.endswith(('.xml', '.iso')):
        raise argparse.ArgumentTypeError('Unknown file ending (use either xml or iso)')
    return value


class ResolvedInput:
    def __init__(self, xmlfile, cdrom, tmp):
        self.xmlfile = xmlfile
        self.cdrom = cdrom
        self._tmp = tmp


def resolve_input(args):
    cdrom = None
    tmp = None

    if args.input.endswith('.xml'):
        xmlfile = args.input
    else:
        tmp = extract_cdrom(args.input)
        xmlfile = tmp.fname('source.xml')
        cdrom = args.input

    return ResolvedInput(xmlfile, cdrom, tmp)


def add_output_argument(f):
    return add_argument('--output', dest='outdir',
                        type=os.path.abspath,
                        help='directory where to save downloaded Files')(f)


def add_submit_arguments(f):
    f = add_argument('--skip-download', action='store_true',
                     dest='skip_download', default=False,
                     help='Skip downloading generated Files')(f)

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


class ProjectBackend(abc.ABC):
    outdir = None

    def check_preprocessed_xml(self, xmlfile, cdrom):
        pass

    @abc.abstractmethod
    def create_project(self, xmlfile):
        ...

    @abc.abstractmethod
    def set_cdrom(self, prjdir, cdrom):
        ...

    @abc.abstractmethod
    def set_base_image(self, prjdir, base_image):
        ...

    @abc.abstractmethod
    def build(self, prjdir, build_bin, build_sources, has_cdrom, uploaded_base_image_path):
        ...

    @abc.abstractmethod
    def wait_busy(self, prjdir):
        ...

    @abc.abstractmethod
    def build_sdk(self, prjdir):
        ...

    @abc.abstractmethod
    def dump_file(self, prjdir, filename, dest):
        ...

    @abc.abstractmethod
    def get_files(self, prjdir, outdir):
        ...

    @abc.abstractmethod
    def del_project(self, prjdir):
        ...

    @abc.abstractmethod
    def recovery_hint(self, prjdir):
        ...

    @abc.abstractmethod
    def download_hint(self, prjdir):
        ...


def build_and_dl_result(backend, xmlfile, cdrom, base_image, args, *, xmlfile_base=None):
    with preprocess_file(xmlfile, variants=args.variants, sshport=args.sshport,
                         soapport=args.soapport, xmlfile_base=xmlfile_base) as xmlfile:
        backend.check_preprocessed_xml(xmlfile, cdrom)
        prjdir = backend.create_project(xmlfile)

    if args.writeproject:
        pathlib.Path(args.writeproject).write_text(prjdir)

    if cdrom is not None:
        print('Copying CDROM into project. This might take a while')
        backend.set_cdrom(prjdir, cdrom)
        print('Copy finished')

    uploaded_base_image_path = None
    if base_image is not None:
        print('Copying base image into project. This might take a while')
        uploaded_base_image_path = backend.set_base_image(prjdir, base_image)
        print('Copy finished')

    backend.build(prjdir, args.build_bin, args.build_sources, bool(cdrom),
                  uploaded_base_image_path)

    print('Build started, waiting till it finishes')

    try:
        for msg in backend.wait_busy(prjdir):
            print(msg)
    except Exception as e:
        raise with_cli_details(e, 133, textwrap.dedent("""
            Build Failed
            """) + backend.recovery_hint(prjdir))

    print('')
    print('Build finished !')
    print('')

    if args.build_sdk:
        backend.build_sdk(prjdir)

        print('SDK Build started, waiting till it finishes')

        try:
            for msg in backend.wait_busy(prjdir):
                print(msg)
        except Exception:
            print('Waiting for the SDK build Failed', file=sys.stderr)
            print('', file=sys.stderr)
            print(backend.recovery_hint(prjdir), file=sys.stderr)
            sys.exit(135)

        print('')
        print('SDK Build finished !')
        print('')

    try:
        backend.dump_file(prjdir, 'validation.txt', sys.stdout.buffer)
        sys.stdout.buffer.flush()
    except Exception:
        print(
            'Project failed to generate validation.txt',
            file=sys.stderr)
        print('Getting log.txt', file=sys.stderr)
        try:
            backend.dump_file(prjdir, 'log.txt', sys.stdout.buffer)
            sys.stdout.buffer.flush()
        except Exception as e:
            raise with_cli_details(e, 137, textwrap.dedent('Failed to dump log.txt'))
        sys.exit(136)

    if args.skip_download:
        print('')
        print('Listing available files:')
        print('')
        for file in backend.get_files(prjdir, None):
            print(f'{file.name}\t{file.description}')

        print('')
        print(backend.download_hint(prjdir))
    else:
        print('')
        print('Getting generated Files')
        print('')

        print(f'Saving generated Files to {backend.outdir}')

        for file in backend.get_files(prjdir, backend.outdir):
            print(f'{file.name}\t{file.description}')

        if not args.keep_files:
            backend.del_project(prjdir)


def build_with_repodir_and_dl_result(backend, xmlfile, cdrom, base_image, args, *,
                                     repodir_base, xmlfile_base=None):
    fname = f'elbe-repodir-{time.time_ns()}.xml'
    preprocess_xmlfile = pathlib.Path(repodir_base) / fname
    try:
        with Repodir(xmlfile, preprocess_xmlfile):
            build_and_dl_result(backend, preprocess_xmlfile, cdrom, base_image, args,
                                xmlfile_base=xmlfile_base)
    except RepodirError as err:
        raise with_cli_details(err, 127, 'elbe repodir failed')
