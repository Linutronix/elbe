# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2014-2018 Linutronix GmbH
# SPDX-FileCopyrightText: 2016 Claudius Heine <ch@denx.de>

import binascii
import logging
import os
import socket
import sys
import time
from datetime import datetime
from http.client import BadStatusLine
from urllib.error import URLError

import debian.deb822

from suds.client import Client

from elbepack.config import cfg
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
