# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Linutronix GmbH

import argparse
import datetime
import ipaddress
import os
import socket
import subprocess
import sys

from elbepack.buildsubmitaction import (
    add_submit_arguments,
    extract_cdrom,
    submit_with_repodir_and_dl_result,
)
from elbepack.cli import add_argument, add_arguments_from_decorated_function
from elbepack.commands.preprocess import add_xmlpreprocess_passthrough_arguments
from elbepack.config import add_arguments_soapclient
from elbepack.soapclient import ElbeSoapClient
from elbepack.soaphelper import is_soap_port_reachable, test_soap_communication


def _is_loopback_host(host):
    """
    Whether `host` resolves exclusively to loopback addresses.

    Used to decide whether it is safe to transparently start a local
    daemon: never do this for a host that might be a remote machine the
    user pointed at on purpose.
    """
    try:
        infos = socket.getaddrinfo(host, None)
    except OSError:
        return False

    return all(ipaddress.ip_address(info[4][0]).is_loopback for info in infos)


def _start_local_daemon(host, port):
    print(f'No ELBE build daemon reachable on {host}:{port}, starting one locally...')
    ps = subprocess.Popen([
        sys.executable, '-P', '-m', 'elbepack',
        'daemon', '--host', host, '--port', str(port)
    ])
    # When a process object is not wait()ed for, the subprocess module raises a
    # ResourceWarning. Inhibit this warning: the daemon is meant to keep running
    # detached from this process (e.g. to serve subsequent "elbe build"/
    # "elbe control" calls in the same container), so it is never wait()ed for.
    ps.returncode = 0


@add_submit_arguments
@add_argument(
    '--no-local-daemon', action='store_true', dest='no_local_daemon',
    help="Don't automatically start a local 'elbe daemon' if --host/--port "
         'is not reachable yet; fail instead. Has no effect if --host is '
         'not a loopback address, since a local daemon is never started '
         'in that case regardless of this flag.')
@add_argument('input', metavar='<xmlfile> | <isoimage>')
def _build(args):
    if args.outdir is None:
        args.outdir = os.path.abspath(
            'elbe-build-' + datetime.datetime.now().strftime('%Y%m%d-%H%M%S'))

    control = ElbeSoapClient.from_args(args)

    if not is_soap_port_reachable(control):
        if args.no_local_daemon or not _is_loopback_host(args.soaphost):
            print(
                f'Cannot reach an ELBE build daemon on {args.soaphost}:{args.soapport}.\n\n'
                "Check that the ELBE build daemon ('elbe daemon') is running and "
                'reachable, or drop --no-local-daemon to let this command start '
                'one locally (only possible when --host is a loopback address).',
                file=sys.stderr)
            sys.exit(14)

        _start_local_daemon(args.soaphost, args.soapport)
        test_soap_communication(control)

    control.connect()

    cdrom = None
    xmlfile = args.input
    if xmlfile.endswith('.iso'):
        tmp = extract_cdrom(xmlfile)
        cdrom = xmlfile
        xmlfile = tmp.fname('source.xml')
    elif not xmlfile.endswith('.xml'):
        args.parser.error('Unknown file ending (use either xml or iso)')

    submit_with_repodir_and_dl_result(control, xmlfile, cdrom, args.base_image, args)


def run_command(argv):
    aparser = argparse.ArgumentParser(prog='elbe build')

    add_arguments_soapclient(aparser)
    add_xmlpreprocess_passthrough_arguments(aparser)
    add_arguments_from_decorated_function(aparser, _build)

    args = aparser.parse_args(argv)
    args.parser = aparser

    _build(args)
