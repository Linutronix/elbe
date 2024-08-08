# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2015-2018 Linutronix GmbH
# SPDX-FileCopyrightText: 2015 Silvio Fricke <silvio.fricke@gmail.com>

import argparse
import os
import subprocess
import sys
import textwrap
import time

import elbepack
import elbepack.initvm
from elbepack.cli import CliError, add_argument, with_cli_details
from elbepack.config import add_argument_sshport, add_arguments_soapclient
from elbepack.directories import run_elbe
from elbepack.elbexml import ElbeXML, ValidationError, ValidationMode
from elbepack.filesystem import TmpdirFilesystem
from elbepack.init import create_initvm
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


def _submit_with_repodir_and_dl_result(control, xmlfile, cdrom, args):
    fname = f'elbe-repodir-{time.time_ns()}.xml'
    preprocess_xmlfile = os.path.join(os.path.dirname(xmlfile), fname)
    try:
        with Repodir(xmlfile, preprocess_xmlfile):
            _submit_and_dl_result(control, preprocess_xmlfile, cdrom, args)
    except RepodirError as err:
        raise with_cli_details(err, 127, 'elbe repodir failed')
    finally:
        os.remove(preprocess_xmlfile)


def _submit_and_dl_result(control, xmlfile, cdrom, args):

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

    control.service.build(prjdir, args.build_bin, args.build_sources, bool(cdrom))

    print('Build started, waiting till it finishes')

    try:
        for msg in control.wait_busy(prjdir):
            print(msg)
    except Exception as e:
        raise with_cli_details(e, 133, textwrap.dedent(f"""
            elbe control wait_busy Failed

            The project will not be deleted from the initvm.
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
            print('The project will not be deleted from the initvm.',
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

        files = control.get_files(prjdir, args.outdir)
        for file in files:
            print(f'{file.name}\t{file.description}')

        if not args.keep_files:
            run_elbe(['control', 'del_project', prjdir], check=True)


def _extract_cdrom(cdrom):
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
            This is not supported by 'elbe initvm'."""))

    try:
        exml = ElbeXML(
            tmp.fname('source.xml'),
            url_validation=ValidationMode.NO_CHECK)
    except ValidationError as e:
        raise with_cli_details(e, 141, textwrap.dedent("""
            Iso image does contain a source.xml file.
            But that xml does not validate correctly."""))

    print('Iso Image with valid source.xml detected !')
    print(f'Image was generated using Elbe Version {exml.get_elbe_version()}')

    return tmp


def _add_submit_arguments(f):
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
                     help="don't delete elbe project files in initvm")(f)

    f = add_argument('--writeproject', dest='writeproject', default=None,
                     help='write project name to file')(f)

    f = add_argument('--build-sdk', dest='build_sdk', action='store_true', default=False,
                     help="Also make 'initvm submit' build an SDK.")(f)

    return f


@_add_initvm_from_args_arguments
@add_argument('--fail-on-warning', action='store_true',
              dest='fail_on_warning', default=False,
              help=argparse.SUPPRESS)
@_add_submit_arguments
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
            tmp = _extract_cdrom(args.input)

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

        _submit_with_repodir_and_dl_result(initvm.control, xmlfile, cdrom, args)


@_add_initvm_from_args_arguments
@_add_submit_arguments
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
        tmp = _extract_cdrom(args.input)
        xmlfile = tmp.fname('source.xml')
        cdrom = args.input
    else:
        args.parser.error('Unknown file ending (use either xml or iso)')

    _submit_with_repodir_and_dl_result(initvm.control, xmlfile, cdrom, args)


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
        *ssh, 'root@localhost', 'systemctl', 'restart', 'python3-elbe-daemon',
    ], check=True)


initvm_actions = {
    'start':   _start,
    'ensure':  _ensure,
    'stop':    _stop,
    'destroy': _destroy,
    'attach':  _attach,
    'create':  _create,
    'submit':  _submit,
    'sync':    _sync,
}
