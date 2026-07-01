# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2015-2018 Linutronix GmbH
# SPDX-FileCopyrightText: 2015 Silvio Fricke <silvio.fricke@gmail.com>

import argparse
import os
import subprocess
import sys
import textwrap

import elbepack
import elbepack.initvm
from elbepack.buildsubmitaction import (
    add_submit_arguments,
    extract_cdrom,
    submit_with_repodir_and_dl_result,
)
from elbepack.cli import CliError, add_argument
from elbepack.config import add_argument_sshport, add_arguments_soapclient
from elbepack.elbexml import ValidationError
from elbepack.init import create_initvm
from elbepack.soapclient import ElbeSoapClient
from elbepack.treeutils import etree
from elbepack.xmlpreprocess import preprocess_file


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


@_add_initvm_from_args_arguments
@add_argument('--fail-on-warning', action='store_true',
              dest='fail_on_warning', default=False,
              help=argparse.SUPPRESS)
@add_submit_arguments
@add_argument('input', nargs='?', metavar='<xmlfile> | <isoimage>')
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

    # Init cdrom to None, if we detect it, we set it
    cdrom = None

    if args.input is not None:
        if args.input.endswith('.xml'):
            # We have an xml file, use that for elbe init
            xmlfile = args.input
            try:
                xml = etree(xmlfile)
            except ValidationError as e:
                print(f'XML file is invalid: {e}')
            # Use default XML if no initvm was specified
            if not xml.has('initvm'):
                xmlfile = os.path.join(
                    elbepack.__path__[0], 'init/default-init.xml')

        elif args.input.endswith('.iso'):
            # We have an iso image, extract xml from there.
            tmp = extract_cdrom(args.input)

            xmlfile = tmp.fname('source.xml')
            cdrom = args.input
        else:
            args.parser.error('Unknown file ending (use either xml or iso)')
    else:
        # No xml File was specified, build the default elbe-init-with-ssh
        xmlfile = os.path.join(
            elbepack.__path__[0],
            'init/default-init.xml')

    with preprocess_file(xmlfile, variants=args.variants, sshport=args.sshport,
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
        )

    initvm = _initvm_from_args(args)

    initvm._build()
    initvm.start()
    initvm.ensure()

    if args.input is not None:
        # If provided xml file has no initvm section xmlfile is set to a
        # default initvm XML file. But we need the original file here.
        if args.input.endswith('.xml'):
            # Stop here if no project node was specified.
            try:
                x = etree(args.input)
            except ValidationError as e:
                print(f'XML file is invalid: {e}')
                sys.exit(149)
            if not x.has('project'):
                print("elbe initvm ready: use 'elbe initvm submit "
                      "myproject.xml' to build a project")
                sys.exit(0)

            xmlfile = args.input
        elif cdrom is not None:
            xmlfile = tmp.fname('source.xml')

        submit_with_repodir_and_dl_result(initvm.control, xmlfile, cdrom, args.base_image, args)


@_add_initvm_from_args_arguments
@add_submit_arguments
@add_argument('input', metavar='<xmlfile> | <isoimage>')
def _submit(args):
    initvm = _initvm_from_args(args)

    initvm.ensure()

    # Init cdrom to None, if we detect it, we set it
    cdrom = None

    if args.input.endswith('.xml'):
        # We have an xml file, use that for elbe init
        xmlfile = args.input
    elif args.input.endswith('.iso'):
        # We have an iso image, extract xml from there.
        tmp = extract_cdrom(args.input)
        xmlfile = tmp.fname('source.xml')
        cdrom = args.input
    else:
        args.parser.error('Unknown file ending (use either xml or iso)')

    submit_with_repodir_and_dl_result(initvm.control, xmlfile, cdrom, args.base_image, args)


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
        'root@localhost:/var/cache/elbe/devel'
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
