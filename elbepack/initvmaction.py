# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2015-2018 Linutronix GmbH
# SPDX-FileCopyrightText: 2015 Silvio Fricke <silvio.fricke@gmail.com>

import abc
import argparse
import os
import pathlib
import subprocess
import sys
import textwrap
import time

import elbepack
import elbepack.initvm
from elbepack.buildsubmitaction import (
    XmlOrIso,
    add_exclude_initvm_pkgs_argument,
    add_output_argument,
    add_submit_arguments,
)
from elbepack.cli import CliError, add_argument, with_cli_details
from elbepack.config import add_argument_sshport, add_arguments_soapclient
from elbepack.elbexml import ValidationError
from elbepack.filesystem import size_to_int
from elbepack.init import create_initvm
from elbepack.paths import DEVEL_DIR
from elbepack.repodir import Repodir, RepodirError
from elbepack.soapclient import ElbeSoapClient
from elbepack.treeutils import etree
from elbepack.xmlpreprocess import preprocess_file


prog = os.path.basename(sys.argv[0])


def _add_initvm_from_args_arguments(parser_or_func):
    parser_or_func = add_argument(
        parser_or_func,
        '--qemu',
        action='store_true',
        dest='qemu_mode',
        default=False,
        help='Use QEMU direct instead of libvirtd.')

    parser_or_func = add_argument(
        parser_or_func,
        '--directory',
        dest='directory',
        type=os.path.abspath,
        default=os.getcwd() + '/initvm',
        help='directory, where the initvm resides, default is ./initvm')

    parser_or_func = add_argument(
        parser_or_func,
        '--domain',
        dest='domain',
        default=os.environ.get('ELBE_INITVM_DOMAIN', 'initvm'),
        help='Name of the libvirt initvm')

    parser_or_func = add_arguments_soapclient(parser_or_func)

    return parser_or_func


def _initvm_from_args(args):
    control = ElbeSoapClient.from_args(args)
    if args.qemu_mode:
        return elbepack.initvm.QemuInitVM(args.directory, control=control)
    else:
        return elbepack.initvm.LibvirtInitVM(directory=args.directory,
                                             domain=args.domain,
                                             control=control)


@_add_initvm_from_args_arguments
def _start(args):
    _initvm_from_args(args).start()


@_add_initvm_from_args_arguments
def _ensure(args):
    _initvm_from_args(args).ensure()


@_add_initvm_from_args_arguments
def _stop(args):
    _initvm_from_args(args).stop()


@_add_initvm_from_args_arguments
def _destroy(args):
    _initvm_from_args(args).destroy()


@_add_initvm_from_args_arguments
def _attach(args):
    _initvm_from_args(args).attach()


class ProjectBackend(abc.ABC):
    outdir = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.stop()

    def stop(self):
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


class SoapProjectBackend(ProjectBackend):
    def __init__(self, control, outdir, exclude_initvm_pkgs):
        self.control = control
        self.outdir = outdir
        self.exclude_initvm_pkgs = exclude_initvm_pkgs

    def create_project(self, xmlfile):
        prjdir = self.control.service.new_project()
        self.control.set_xml(prjdir, xmlfile)
        return prjdir

    def set_cdrom(self, prjdir, cdrom):
        self.control.set_cdrom(prjdir, cdrom)

    def set_base_image(self, prjdir, base_image):
        return self.control.set_base_image(prjdir, base_image)

    def build(self, prjdir, build_bin, build_sources, has_cdrom, uploaded_base_image_path):
        self.control.service.build(prjdir, build_bin, build_sources, has_cdrom,
                                   uploaded_base_image_path, self.exclude_initvm_pkgs)

    def wait_busy(self, prjdir):
        yield from self.control.wait_busy(prjdir)

    def build_sdk(self, prjdir):
        self.control.service.build_sdk(prjdir)

    def dump_file(self, prjdir, filename, dest):
        for chunk in self.control.dump_file(prjdir, filename):
            dest.write(chunk)

    def get_files(self, prjdir, outdir):
        return self.control.get_files(prjdir, outdir)

    def del_project(self, prjdir):
        self.control.service.del_project(prjdir)

    def recovery_hint(self, prjdir):
        return textwrap.dedent(f"""
            The project will not be deleted from the initvm.
            The files, that have been built, can be downloaded using:
            {prog} control get_files --output "{self.outdir}" "{prjdir}"

            The project can then be removed using:
            {prog} control del_project "{prjdir}\"""")

    def download_hint(self, prjdir):
        return f'Get Files with: elbe control get_file "{prjdir}" <filename>'


def _submit_with_repodir_and_dl_result(control, xmlfile, cdrom, base_image, args):
    with SoapProjectBackend(control, args.outdir, args.exclude_initvm_pkgs) as backend:
        build_with_repodir_and_dl_result(backend, xmlfile, cdrom, base_image, args,
                                         repodir_base=xmlfile.parent,
                                         xmlfile_base=xmlfile)


def build_with_repodir_and_dl_result(backend, xmlfile, cdrom, base_image, args, *,
                                     repodir_base, xmlfile_base=None):
    fname = f'elbe-repodir-{time.time_ns()}.xml'
    preprocess_xmlfile = repodir_base / fname
    try:
        with Repodir(xmlfile, preprocess_xmlfile):
            build_and_dl_result(backend, preprocess_xmlfile, cdrom, base_image, args,
                                xmlfile_base=xmlfile_base)
    except RepodirError as err:
        raise with_cli_details(err, 127, 'elbe repodir failed')


def build_and_dl_result(backend, xmlfile, cdrom, base_image, args, *, xmlfile_base=None):
    with preprocess_file(xmlfile, variants=args.variants, sshport=args.sshport,
                         soapport=args.soapport, xmlfile_base=xmlfile_base) as xmlfile:
        prjdir = backend.create_project(xmlfile)

    if args.writeproject:
        args.writeproject.write_text(prjdir)

    if cdrom is not None:
        print('Uploading CDROM. This might take a while')
        backend.set_cdrom(prjdir, cdrom)
        print('Upload finished')

    uploaded_base_image_path = None
    if base_image is not None:
        print('Uploading base image. This might take a while')
        uploaded_base_image_path = backend.set_base_image(prjdir, base_image)
        print('Upload finished')

    backend.build(prjdir, args.build_bin, args.build_sources, bool(cdrom),
                  uploaded_base_image_path)

    print('Build started, waiting till it finishes')

    try:
        for msg in backend.wait_busy(prjdir):
            print(msg)
    except Exception as e:
        raise with_cli_details(e, 133, textwrap.dedent("""
            elbe control wait_busy Failed
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
            print('elbe control wait_busy Failed, while waiting for the SDK',
                  file=sys.stderr)
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


@_add_initvm_from_args_arguments
@add_argument('--fail-on-warning', action='store_true',
              dest='fail_on_warning', default=False,
              help=argparse.SUPPRESS)
@add_submit_arguments
@add_argument('--size', help='Disk size', type=size_to_int)
@add_output_argument
@add_exclude_initvm_pkgs_argument
@add_argument('input', nargs='?', type=XmlOrIso, default=XmlOrIso(),
              metavar='<xmlfile> | <isoimage>')
def _create(args):
    # Upgrade from older versions which used tmux
    try:
        subprocess.run(['tmux', 'has-session', '-t', 'ElbeInitVMSession'],
                       stderr=subprocess.DEVNULL, check=True)
        raise CliError(143, textwrap.dedent("""
            ElbeInitVMSession exists in tmux.
            It may belong to an old elbe version.
            Please stop it to prevent interfering with this version."""))
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass

    with args.input as resolved:
        xmlfile = resolved.xmlfile
        cdrom = resolved.cdrom

        if xmlfile is None:
            # No xml File was specified, build the default elbe-init-with-ssh
            initxml = os.path.join(elbepack.__path__[0], 'init/default-init.xml')
        elif cdrom is None:
            # We have an xml file, use that for elbe init
            try:
                xml = etree(xmlfile)
            except ValidationError as e:
                print(f'XML file is invalid: {e}')
            # Use default XML if no initvm was specified
            if xml.has('initvm'):
                initxml = xmlfile
            else:
                initxml = os.path.join(elbepack.__path__[0], 'init/default-init.xml')
        else:
            initxml = xmlfile

        with preprocess_file(initxml, variants=args.variants, sshport=args.sshport,
                             soapport=args.soapport) as preproc:
            create_initvm(
                args.domain,
                preproc,
                args.directory,
                sshport=args.sshport,
                soapport=args.soapport,
                cdrom=cdrom,
                build_bin=args.build_bin,
                build_sources=args.build_sources,
                fail_on_warning=args.fail_on_warning,
                size=args.size,
            )

        initvm = _initvm_from_args(args)

        initvm._build()
        initvm.start()
        initvm.ensure()

        if xmlfile is not None:
            if cdrom is None:
                # Stop here if no project node was specified.
                try:
                    x = etree(xmlfile)
                except ValidationError as e:
                    print(f'XML file is invalid: {e}')
                    sys.exit(149)
                if not x.has('project'):
                    print("elbe initvm ready: use 'elbe initvm submit "
                          "myproject.xml' to build a project")
                    sys.exit(0)

            _submit_with_repodir_and_dl_result(
                initvm.control, xmlfile, cdrom, args.base_image, args)


@_add_initvm_from_args_arguments
@add_submit_arguments
@add_output_argument
@add_exclude_initvm_pkgs_argument
@add_argument('input', type=XmlOrIso, metavar='<xmlfile> | <isoimage>')
def _submit(args):
    initvm = _initvm_from_args(args)

    initvm.ensure()

    with args.input as resolved:
        _submit_with_repodir_and_dl_result(
            initvm.control, resolved.xmlfile, resolved.cdrom, args.base_image, args)


@add_argument_sshport
def _sync(args):
    top_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
    excludes = ['.git*', '*.pyc', 'elbe-build*', 'initvm', '__pycache__', 'docs', 'examples']
    ssh = ['ssh', '-p', str(args.sshport), '-oUserKnownHostsFile=/dev/null']
    subprocess.run([
        'rsync', '--info=name1,stats1', '--archive', '--times',
        *[arg for e in excludes for arg in ('--exclude', e)],
        '--rsh', ' '.join(ssh),
        '--chown=root:root',
        f'{top_dir}/elbe',
        f'{top_dir}/elbepack',
        f'root@localhost:{DEVEL_DIR}'
    ], check=True)
    subprocess.run([
        *ssh, '-n', 'root@localhost', 'systemctl', 'restart', 'python3-elbe-daemon',
    ], check=True)


@add_argument_sshport
def _ssh(args):
    subprocess.run([
        'ssh', '-p', str(args.sshport), '-oUserKnownHostsFile=/dev/null', 'root@localhost',
    ], check=False)


initvm_actions = {
    'start':   _start,
    'ensure':  _ensure,
    'stop':    _stop,
    'destroy': _destroy,
    'attach':  _attach,
    'create':  _create,
    'submit':  _submit,
    'sync':    _sync,
    'ssh':     _ssh,
}
