# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2014-2018 Linutronix GmbH
# SPDX-FileCopyrightText: 2016 Claudius Heine <ch@denx.de>

import binascii
import fnmatch
import logging
import os
import socket
import sys
import time
from datetime import datetime
from http.client import BadStatusLine
from urllib.error import URLError

import debian.deb822

from suds import WebFault
from suds.client import Client

from elbepack.cli import add_argument
from elbepack.config import cfg
from elbepack.elbexml import ElbeXML, ValidationMode
from elbepack.version import elbe_version


class ElbeVersionMismatch(RuntimeError):
    def __init__(self, client_version, server_version):
        self.client_version = client_version
        self.server_version = server_version
        super().__init__(f'Client: {client_version} Server: {server_version}')

    @classmethod
    def check(cls, client_version, server_version):
        if client_version != server_version:
            raise cls(client_version, server_version)


def set_suds_debug(debug):
    if debug:
        logging.basicConfig(level=logging.INFO)
        logging.getLogger('suds.client').setLevel(logging.DEBUG)
        logging.getLogger('suds.transport').setLevel(logging.DEBUG)
        logging.getLogger('suds.xsd.schema').setLevel(logging.DEBUG)
        logging.getLogger('suds.wsdl').setLevel(logging.DEBUG)
        logging.getLogger('suds.resolver').setLevel(logging.DEBUG)
        logging.getLogger('suds.umx.typed').setLevel(logging.DEBUG)
    else:
        logging.basicConfig(level=logging.CRITICAL)
        logging.getLogger('suds.umx.typed').setLevel(logging.ERROR)
        logging.getLogger('suds.client').setLevel(logging.CRITICAL)


class ElbeSoapClient:
    def __init__(self, host, port, user, passwd, retries=10, debug=False):

        # Mess with suds logging, for debug, or squelch warnings
        set_suds_debug(debug)

        # Attributes
        self.wsdl = 'http://' + host + ':' + str(port) + '/soap/?wsdl'
        control = None
        current_retries = 0

        # Loop and try to connect
        while control is None:
            current_retries += 1
            try:
                control = Client(self.wsdl, timeout=cfg['soaptimeout'])
            except URLError as e:
                if current_retries > retries:
                    raise e
                time.sleep(1)
            except socket.error as e:
                if current_retries > retries:
                    raise e
                time.sleep(1)
            except BadStatusLine as e:
                if current_retries > retries:
                    raise e
                time.sleep(1)

        # Make sure, that client.service still maps
        # to the service object.
        self.service = control.service

        ElbeVersionMismatch.check(elbe_version, self.service.get_version())

        # We have a Connection, now login
        self.service.login(user, passwd)

    def download_file(self, builddir, filename, dst_fname):
        fp = open(dst_fname, 'wb')
        part = 0

        # XXX the retry logic might get removed in the future, if the error
        # doesn't occur in real world. If it occurs, we should think about
        # the root cause instead of stupid retrying.
        retry = 5

        while True:
            try:
                ret = self.service.get_file(builddir, filename, part)
            except BadStatusLine as e:
                retry = retry - 1

                print(f'get_file part {part} failed, retry {retry} times',
                      file=sys.stderr)
                print(str(e), file=sys.stderr)
                print(repr(e.line), file=sys.stderr)

                if not retry:
                    fp.close()
                    print('file transfer failed', file=sys.stderr)
                    sys.exit(170)

            if ret == 'FileNotFound':
                print(ret, file=sys.stderr)
                sys.exit(171)
            if ret == 'EndOfFile':
                fp.close()
                return

            fp.write(binascii.a2b_base64(ret))
            part = part + 1


def _add_project_dir_argument(f):
    return add_argument('project_dir')(f)


def _client_action_upload_file(append, build_dir, filename):
    size = 1024 * 1024

    with open(filename, 'rb') as f:

        while True:

            bin_data = f.read(size)
            data = binascii.b2a_base64(bin_data)

            if not isinstance(data, str):
                data = data.decode('ascii')

            append(build_dir, data)

            if len(bin_data) != size:
                break


@_add_project_dir_argument
def _remove_log(client, args):
    client.service.rm_log(args.project_dir)


def _list_projects(client, args):
    projects = client.service.list_projects()

    try:
        for p in projects.SoapProject:
            print(
                f'{p.builddir}\t{p.name}\t{p.version}\t{p.status}\t'
                f'{p.edit}')
    except AttributeError:
        print('No projects configured in initvm')


def _list_users(client, args):
    users = client.service.list_users()

    for u in users.string:
        print(u)


@add_argument('name')
@add_argument('fullname')
@add_argument('password')
@add_argument('email')
def _add_user(client, args):
    try:
        client.service.add_user(args.name, args.fullname, args.password, args.email, False)
    except WebFault as e:
        if not hasattr(e.fault, 'faultstring'):
            raise

        if not e.fault.faultstring.endswith('already exists in the database'):
            raise

        # when we get here, the user we wanted to create already exists.
        # that is fine, and we dont need to do anything now.


def _create_project(client, args):
    uuid = client.service.new_project()
    print(uuid)


@_add_project_dir_argument
def _reset_project(client, args):
    client.service.reset_project(args.project_dir)


@_add_project_dir_argument
def _delete_project(client, args):
    client.service.del_project(args.project_dir)


@_add_project_dir_argument
@add_argument('xml')
def _set_xml(client, args):
    builddir = args.project_dir
    filename = args.xml

    try:
        x = ElbeXML(
            filename,
            skip_validate=True,
            url_validation=ValidationMode.NO_CHECK)
    except IOError:
        print(f'{filename} is not a valid elbe xml file')
        sys.exit(177)

    if not x.has('target'):
        print("<target> is missing, this file can't be built in an initvm",
              file=sys.stderr)
        sys.exit(178)

    size = 1024 * 1024
    part = 0
    with open(filename, 'rb') as fp:
        while True:

            xml_base64 = binascii.b2a_base64(fp.read(size))

            if not isinstance(xml_base64, str):
                xml_base64 = xml_base64.decode('ascii')

            # finish upload
            if len(xml_base64) == 1:
                part = client.service.upload_file(builddir,
                                                  'source.xml',
                                                  xml_base64,
                                                  -1)
            else:
                part = client.service.upload_file(builddir,
                                                  'source.xml',
                                                  xml_base64,
                                                  part)
            if part == -1:
                print('project busy, upload not allowed')
                return part
            if part == -2:
                print('upload of xml finished')
                return 0


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
    part = 0
    while True:
        ret = client.service.get_file(args.project_dir, args.file, part)
        if ret == 'FileNotFound':
            print(ret, file=sys.stderr)
            sys.exit(187)
        if ret == 'EndOfFile':
            return

        os.write(sys.stdout.fileno(), binascii.a2b_base64(ret))
        part = part + 1


@add_argument('--output', required=True, help='Output files to <directory>')
@add_argument('--pbuilder-only', action='store_true', dest='pbuilder_only',
              help='Only list/download pbuilder Files')
@add_argument('--matches', dest='matches', default=False,
              help='Select files based on wildcard expression.')
@_add_project_dir_argument
def _get_files(client, args):
    files = client.service.get_files(args.project_dir)

    nfiles = 0

    for f in files[0]:
        if (args.pbuilder_only and not f.name.startswith('pbuilder_cross')
                and not f.name.startswith('pbuilder')):
            continue

        if args.matches and not fnmatch.fnmatch(f.name, args.matches):
            continue

        nfiles += 1
        try:
            print(f'{f.name} \t({f.description})')
        except AttributeError:
            print(f'{f.name}')

        dst = os.path.abspath(args.output)
        os.makedirs(dst, exist_ok=True)
        dst_fname = str(os.path.join(dst, os.path.basename(f.name)))
        client.download_file(args.project_dir, f.name, dst_fname)

    if nfiles == 0:
        sys.exit(189)


@_add_project_dir_argument
def _wait_busy(client, args):
    while True:
        try:
            msg = client.service.get_project_busy(args.project_dir)
        # TODO the root cause of this problem is unclear. To enable a
        # get more information print the exception and retry to see if
        # the connection problem is just a temporary problem. This
        # code should be reworked as soon as it's clear what is going on
        # here
        except socket.error as e:
            print(str(e), file=sys.stderr)
            print('socket error during wait busy occured, retry..',
                  file=sys.stderr)
            continue

        if not msg:
            time.sleep(0.1)
            continue

        if msg == 'ELBE-FINISH':
            break

        print(msg)

    # exited the while loop -> the project is not busy anymore,
    # check, whether everything is ok.

    prj = client.service.get_project(args.project_dir)
    if prj.status != 'build_done':
        print(
            'Project build was not successful, current status: '
            f'{prj.status}',
            file=sys.stderr)
        sys.exit(191)


@_add_project_dir_argument
@add_argument('cdrom_file')
def _set_cdrom(client, args):
    client.service.start_cdrom(args.project_dir)
    _client_action_upload_file(client.service.append_cdrom, args.project_dir, args.cdrom_file)
    client.service.finish_cdrom(args.project_dir)


@_add_project_dir_argument
@add_argument('orig_file')
def _set_orig(client, args):
    client.service.start_upload_orig(args.project_dir, os.path.basename(args.orig_file))
    _client_action_upload_file(client.service.append_upload_orig, args.project_dir, args.orig_file)
    client.service.finish_upload_orig(args.project_dir)


@add_argument('--profile', dest='profile', default='',
              help='Make pbuilder commands build the specified profile')
@add_argument('--cross', dest='cross', action='store_true',
              help='Creates an environment for crossbuilding if '
                   'combined with create. Combined with build it'
                   ' will use this environment.')
@add_argument('--cpuset', default=-1, type=int,
              help='Limit cpuset of pbuilder commands (bitmask)'
                   '(defaults to -1 for all CPUs)')
@_add_project_dir_argument
@add_argument('pdebuild_file')
def _set_pdebuild(client, args):
    client.service.start_pdebuild(args.project_dir)
    _client_action_upload_file(client.service.append_pdebuild, args.project_dir, args.pdebuild_file)
    client.service.finish_pdebuild(args.project_dir, args.cpuset, args.profile, args.cross)


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


client_actions = {
    'rm_log':               _remove_log,
    'list_projects':        _list_projects,
    'list_users':           _list_users,
    'add_user':             _add_user,
    'create_project':       _create_project,
    'reset_project':        _reset_project,
    'del_project':          _delete_project,
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
}


class RepoAction:
    repoactiondict = {}

    @classmethod
    def register(cls, action):
        cls.repoactiondict[action.tag] = action

    @classmethod
    def print_actions(cls):
        print('available subcommands are:', file=sys.stderr)
        for a in cls.repoactiondict:
            print(f'   {a}', file=sys.stderr)

    def __new__(cls, node):
        action = cls.repoactiondict[node]
        return object.__new__(action)

    def execute(self, _client, _opt, _args):
        raise NotImplementedError('execute() not implemented')


class ListPackagesAction(RepoAction):

    tag = 'list_packages'

    def execute(self, client, _opt, args):
        if len(args) != 1:
            print(
                'usage: elbe prjrepo list_packages <project_dir>',
                file=sys.stderr)
            sys.exit(199)

        builddir = args[0]
        print(client.service.list_packages(builddir))


RepoAction.register(ListPackagesAction)


class DownloadAction(RepoAction):

    tag = 'download'

    def execute(self, client, _opt, args):
        if len(args) != 1:
            print('usage: elbe prjrepo download <project_dir>',
                  file=sys.stderr)
            sys.exit(200)

        builddir = args[0]
        filename = 'repo.tar.gz'
        client.service.tar_prjrepo(builddir, filename)

        dst_fname = os.path.join(
            '.',
            'elbe-projectrepo-' +
            datetime.now().strftime('%Y%m%d-%H%M%S') +
            '.tar.gz')

        client.download_file(builddir, filename, dst_fname)
        print(f'{dst_fname} saved')


RepoAction.register(DownloadAction)


class UploadPackageAction(RepoAction):

    tag = 'upload_pkg'

    @staticmethod
    def upload_file(client, f, builddir):
        # Uploads file f into builddir in intivm
        size = 1024 * 1024
        part = 0
        with open(f, 'rb') as fp:
            while True:

                xml_base64 = binascii.b2a_base64(fp.read(size))

                if not isinstance(xml_base64, str):
                    xml_base64 = xml_base64.decode('ascii')

                # finish upload
                if len(xml_base64) == 1:
                    part = client.service.upload_file(builddir,
                                                      os.path.basename(f),
                                                      xml_base64,
                                                      -1)
                else:
                    part = client.service.upload_file(builddir,
                                                      os.path.basename(f),
                                                      xml_base64,
                                                      part)
                if part == -1:
                    print('project busy, upload not allowed')
                    return -1
                if part == -2:
                    print('Upload of package finished.')
                    break

    def execute(self, client, _opt, args):
        if len(args) != 2:
            print(
                'usage: elbe prjrepo upload_pkg <project_dir> <deb/dsc/changes file>',
                file=sys.stderr)
            sys.exit(201)

        builddir = args[0]
        filename = args[1]

        print('\n--------------------------')
        print('Upload and Include Package')
        print('--------------------------')
        print('Check files...')

        filetype = os.path.splitext(filename)[1]

        # Check filetype
        if filetype not in ['.dsc', '.deb', '.changes']:
            print('Error: Only .dsc, .deb or .changes files allowed to upload.')
            sys.exit(202)

        files = [filename]  # list of all files which will be uploaded

        # Parse .dsc-File and append neccessary source files to files
        if filetype == '.dsc':
            for f in debian.deb822.Dsc(open(filename))['Files']:
                files.append(f['name'])

        if filetype == '.changes':
            for f in debian.deb822.Changes(open(filename))['Files']:
                files.append(f['name'])

        # Check whether all files are available
        abort = False
        for f in files:
            if not os.path.isfile(f):
                print(f'File {f} not found.')
                abort = True
        # Abort if one or more source files are missing
        if abort:
            sys.exit(203)

        print('Start uploading file(s)...')
        for f in files:
            print(f'Upload {f}...')
            self.upload_file(client, f, builddir)

        print('Including Package in initvm...')
        client.service.include_package(builddir, os.path.basename(filename))


RepoAction.register(UploadPackageAction)
