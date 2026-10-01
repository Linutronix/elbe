# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Linutronix GmbH

import argparse
import datetime
import os
import pathlib
import subprocess
import sys
import textwrap

from elbepack.cli import CliError, add_argument, with_cli_details
from elbepack.elbexml import ElbeXML, ValidationError
from elbepack.filesystem import TmpdirFilesystem


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


class XmlOrIso:
    def __init__(self, path=None):
        if path is not None and not path.endswith(('.xml', '.iso')):
            raise argparse.ArgumentTypeError('Unknown file ending (use either xml or iso)')
        self.path = path
        self.xmlfile = None
        self.cdrom = None
        self._tmpdir = None

    def __enter__(self):
        if self.path is None:
            pass
        elif self.path.endswith('.iso'):
            self._tmpdir = extract_cdrom(self.path)
            self.xmlfile = pathlib.Path(self._tmpdir.fname('source.xml'))
            self.cdrom = self.path
        else:
            self.xmlfile = pathlib.Path(self.path)
        return self

    def __exit__(self, exc_type, exc_value, tb):
        if self._tmpdir is not None:
            self._tmpdir.delete()
        return False


def build_dir_type(path=None):
    if path is None:
        path = 'elbe-build-' + datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
    return pathlib.Path(path).absolute()


def add_output_argument(f):
    return add_argument('--output', dest='outdir',
                        type=build_dir_type,
                        help='directory where to save downloaded Files')(f)


def add_exclude_initvm_pkgs_argument(f):
    return add_argument('--exclude-initvm-pkgs', action='store_true',
                        dest='exclude_initvm_pkgs', default=False,
                        help='Exclude initvm packages from CDROM generation')(f)


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
