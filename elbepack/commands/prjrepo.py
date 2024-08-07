# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2017 Linutronix GmbH

import argparse
import binascii
import os
import socket
import sys
from datetime import datetime
from http.client import BadStatusLine
from urllib.error import URLError

import debian.deb822

from suds import WebFault

from elbepack.cli import add_argument, add_arguments_from_decorated_function
from elbepack.config import add_arguments_soapclient
from elbepack.soapclient import ElbeSoapClient


@add_argument('project_dir')
def _list_packages(client, args):
    for pkg in client.service.list_packages(args.project_dir):
        print(pkg)


@add_argument('project_dir')
def _download(client, args):
    filename = 'repo.tar.gz'
    client.service.tar_prjrepo(args.project_dir, filename)

    dst_fname = os.path.join(
        '.',
        'elbe-projectrepo-' +
        datetime.now().strftime('%Y%m%d-%H%M%S') +
        '.tar.gz')

    client.download_file(args.project_dir, filename, dst_fname)
    print(f'{dst_fname} saved')


def _upload_file(client, f, builddir):
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


@add_argument('project_dir')
@add_argument('package')
def _upload_pkg(client, args):
    print('\n--------------------------')
    print('Upload and Include Package')
    print('--------------------------')
    print('Check files...')

    filetype = os.path.splitext(args.package)[1]

    # Check filetype
    if filetype not in ['.dsc', '.deb', '.changes']:
        print('Error: Only .dsc, .deb or .changes files allowed to upload.')
        sys.exit(202)

    files = [args.package]  # list of all files which will be uploaded

    # Parse .dsc-File and append neccessary source files to files
    if filetype == '.dsc':
        for f in debian.deb822.Dsc(open(args.package))['Files']:
            files.append(f['name'])

    if filetype == '.changes':
        for f in debian.deb822.Changes(open(args.package))['Files']:
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
        _upload_file(client, f, args.project_dir)

    print('Including Package in initvm...')
    client.service.include_package(args.project_dir, os.path.basename(args.package))


_actions = {
    'list_packages': _list_packages,
    'download': _download,
    'upload_pkg': _upload_pkg,
}


def run_command(argv):

    aparser = argparse.ArgumentParser(prog='elbe prjrepo')

    add_arguments_soapclient(aparser)

    subparsers = aparser.add_subparsers(required=True)

    for action_name, do_action in _actions.items():
        action_parser = subparsers.add_parser(action_name)
        action_parser.set_defaults(func=do_action)
        add_arguments_from_decorated_function(action_parser, do_action)

    args = aparser.parse_args(argv)

    control = ElbeSoapClient.from_args(args)

    # Try to connect to initvm via SOAP
    try:
        control.connect()
    except (URLError, socket.error, BadStatusLine):
        print(
            f'Failed to connect to Soap server {args.soaphost}:{args.soapport}\n',
            file=sys.stderr)
        print('', file=sys.stderr)
        print('Check, wether the initvm is actually running.', file=sys.stderr)
        print('try `elbe initvm start`', file=sys.stderr)
        sys.exit(10)

    # Execute command
    try:
        args.func(control, args)
    except WebFault as e:
        print('Server returned an error:', file=sys.stderr)
        print('', file=sys.stderr)
        if hasattr(e.fault, 'faultstring'):
            print(e.fault.faultstring, file=sys.stderr)
        else:
            print(e, file=sys.stderr)
        sys.exit(5)
