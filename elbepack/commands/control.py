# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2014-2017 Linutronix GmbH

import argparse
import json
import os
import socket
import sys
from http.client import BadStatusLine
from urllib.error import URLError

from suds import WebFault

from elbepack.cli import add_argument, add_arguments_from_decorated_function
from elbepack.config import add_arguments_soapclient
from elbepack.soapclient import ElbeSoapClient


def _add_project_dir_argument(f):
    return add_argument('project_dir')(f)


@_add_project_dir_argument
def _remove_log(client, args):
    client.service.rm_log(args.project_dir)


def _list_projects(client, args):
    projects = client.list_projects()
    if not projects:
        print('No projects configured in initvm')
        return

    for p in projects:
        print(f'{p.builddir}\t{p.name}\t{p.version}\t{p.status}\t' f'{p.edit}')


def _create_project(client, args):
    uuid = client.service.new_project()
    print(uuid)


@_add_project_dir_argument
def _reset_project(client, args):
    client.service.reset_project(args.project_dir)


@_add_project_dir_argument
def _delete_project(client, args):
    client.service.del_project(args.project_dir)


def _delete_all_projects(client, args):
    for project in client.list_projects():
        print(f'Deleting {project.builddir} {project.name}')
        client.service.del_project(project.builddir)


@_add_project_dir_argument
@add_argument('xml')
def _set_xml(client, args):
    client.set_xml(args.project_dir, args.xml)


@add_argument('--build-bin', action='store_true', dest='build_bin',
              help='Build binary repository CDROM, for exact reproduction.')
@add_argument('--build-sources', action='store_true', dest='build_sources',
              help='Build source CDROM')
@add_argument('--skip-pbuilder', action='store_true', dest='skip_pbuilder',
              help="skip pbuilder section of XML (don't build packages)")
@_add_project_dir_argument
def _build(client, args):
    client.service.build(args.project_dir, args.build_bin, args.build_sources, args.skip_pbuilder)


@_add_project_dir_argument
def _build_sysroot(client, args):
    client.service.build_sysroot(args.project_dir)


@_add_project_dir_argument
def _build_sdk(client, args):
    client.service.build_sdk(args.project_dir)


@add_argument('--build-bin', action='store_true', dest='build_bin',
              help='Build binary repository CDROM, for exact reproduction.')
@add_argument('--build-sources', action='store_true', dest='build_sources',
              help='Build source CDROM')
@_add_project_dir_argument
def _build_cdroms(client, args):
    if not args.build_bin and not args.build_sources:
        args.parser.error('One of --build-bin or --build-sources needs to be specified')

    client.service.build_cdroms(args.project_dir, args.build_bin, args.build_sources)


@add_argument('--output', required=True, help='Output files to <directory>')
@_add_project_dir_argument
@add_argument('file')
def _get_file(client, args):
    dst = os.path.abspath(args.output)
    os.makedirs(dst, exist_ok=True)
    dst_fname = str(os.path.join(dst, args.file)).encode()

    client.download_file(args.project_dir, args.file, dst_fname)
    print(f'{args.file} saved')


@_add_project_dir_argument
def _build_chroot(client, args):
    client.service.build_chroot_tarball(args.project_dir)


@_add_project_dir_argument
@add_argument('file')
def _dump_file(client, args):
    for chunk in client.dump_file(args.project_dir, args.file):
        sys.stdout.buffer.write(chunk)
    sys.stdout.buffer.flush()


@add_argument('--output', help='Output files to <directory>')
@add_argument('--pbuilder-only', action='store_true', dest='pbuilder_only',
              help='Only list/download pbuilder Files')
@add_argument('--matches', dest='matches', default=False,
              help='Select files based on wildcard expression.')
@_add_project_dir_argument
def _get_files(client, args):
    files = client.get_files(args.project_dir, args.output,
                             pbuilder_only=args.pbuilder_only, wildcard=args.matches)
    if not files:
        sys.exit(189)

    for file in files:
        print(f'{file.name}\t{file.description}')


@_add_project_dir_argument
def _wait_busy(client, args):
    for msg in client.wait_busy(args.project_dir):
        print(msg)


@_add_project_dir_argument
@add_argument('cdrom_file')
def _set_cdrom(client, args):
    client.set_cdrom(args.project_dir, args.cdrom_file)


@_add_project_dir_argument
@add_argument('orig_file')
def _set_orig(client, args):
    client.set_orig(args.project_dir, args.orig_file)


@add_argument('--profile', dest='profile', default='',
              help='Make pbuilder commands build the specified profile')
@add_argument('--cross', dest='cross', action='store_true',
              help='Creates an environment for crossbuilding if '
                   'combined with create. Combined with build it'
                   ' will use this environment.')
@_add_project_dir_argument
@add_argument('pdebuild_file')
def _set_pdebuild(client, args):
    client.set_pdebuild(args.project_dir, args.profile, args.cross)


@add_argument('--cross', dest='cross', action='store_true',
              help='Creates an environment for crossbuilding if '
                   'combined with create. Combined with build it'
                   ' will use this environment.')
@add_argument('--no-ccache', dest='noccache', action='store_true',
              help="Deactivates the compiler cache 'ccache'")
@add_argument('--ccache-size', dest='ccachesize', default='10G',
              help='set a limit for the compiler cache size '
                   '(should be a number followed by an optional '
                   'suffix: k, M, G, T. Use 0 for no limit.)')
@_add_project_dir_argument
def _build_pbuilder(client, args):
    client.service.build_pbuilder(args.project_dir, args.cross, args.noccache, args.ccachesize)


@_add_project_dir_argument
def _update_pbuilder(client, args):
    client.service.update_pbuilder(args.project_dir)


def _python_dict_from_spyne_model(d):
    return {k: getattr(d, k) for k in d.__keylist__}


def _status(client, args):
    json.dump(_python_dict_from_spyne_model(client.service.status()), sys.stdout, indent=2)
    sys.stdout.write('\n')


_client_actions = {
    'rm_log':               _remove_log,
    'list_projects':        _list_projects,
    'create_project':       _create_project,
    'reset_project':        _reset_project,
    'del_project':          _delete_project,
    'del_all_projects':     _delete_all_projects,
    'set_xml':              _set_xml,
    'build':                _build,
    'build_sysroot':        _build_sysroot,
    'build_sdk':            _build_sdk,
    'build_cdroms':         _build_cdroms,
    'get_file':             _get_file,
    'build_chroot_tarball': _build_chroot,
    'dump_file':            _dump_file,
    'get_files':            _get_files,
    'wait_busy':            _wait_busy,
    'set_cdrom':            _set_cdrom,
    'set_orig':             _set_orig,
    'set_pdebuild':         _set_pdebuild,
    'build_pbuilder':       _build_pbuilder,
    'update_pbuilder':      _update_pbuilder,
    'status':               _status,
}


def run_command(argv):

    aparser = argparse.ArgumentParser(prog='elbe control')

    add_arguments_soapclient(aparser)

    subparsers = aparser.add_subparsers(required=True)

    for action_name, do_action in _client_actions.items():
        action_parser = subparsers.add_parser(action_name)
        action_parser.set_defaults(func=do_action)
        add_arguments_from_decorated_function(action_parser, do_action)

    args = aparser.parse_args(argv)
    args.parser = aparser

    control = ElbeSoapClient.from_args(args)

    try:
        control.connect()
    except (URLError, socket.error, BadStatusLine):
        print(
            f'Failed to connect to Soap server {args.soaphost}:{args.soapport}\n',
            file=sys.stderr)
        print('', file=sys.stderr)
        print('Check, whether the initvm is actually running.', file=sys.stderr)
        print("try 'elbe initvm start'", file=sys.stderr)
        sys.exit(13)

    try:
        args.func(control, args)
    except WebFault as e:
        print('Server returned error:', file=sys.stderr)
        print('', file=sys.stderr)
        if hasattr(e.fault, 'faultstring'):
            print(e.fault.faultstring, file=sys.stderr)
        else:
            print(e, file=sys.stderr)
        sys.exit(6)
