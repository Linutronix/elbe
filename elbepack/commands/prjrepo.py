# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2017 Linutronix GmbH

import socket
import sys
from http.client import BadStatusLine
from optparse import OptionGroup, OptionParser
from urllib.error import URLError

from suds import WebFault

from elbepack.config import cfg
from elbepack.soapclient import ElbeSoapClient, RepoAction


def run_command(argv):

    oparser = OptionParser(usage='usage: elbe prjrepo [options] <command>')

    oparser.add_option('--host', dest='host', default=cfg['soaphost'],
                       help='Ip or hostname of elbe-daemon.')

    oparser.add_option('--port', dest='port', default=cfg['soapport'],
                       help='Port of soap itf on elbe-daemon.')

    oparser.add_option('--pass', dest='passwd', default=cfg['elbepass'],
                       help='Password (default is foo).')

    oparser.add_option('--user', dest='user', default=cfg['elbeuser'],
                       help='Username (default is root).')

    oparser.add_option(
        '--retries',
        dest='retries',
        default='10',
        help='How many times to retry the connection to the server before\
                giving up (default is 10 times, yielding 10 seconds).')

    devel = OptionGroup(
        oparser,
        'options for elbe developers',
        "Caution: Don't use these options in a productive environment")
    devel.add_option('--debug', action='store_true',
                     dest='debug', default=False,
                     help='Enable debug mode.')

    (opt, args) = oparser.parse_args(argv)

    if not args:
        print('elbe prjrepo - no subcommand given', file=sys.stderr)
        RepoAction.print_actions()
        return

    # Try to connect to initvm via SOAP
    try:
        control = ElbeSoapClient(
            opt.host,
            opt.port,
            opt.user,
            opt.passwd,
            debug=opt.debug,
            retries=int(
                opt.retries))
    except URLError:
        print(
            f'Failed to connect to Soap server {opt.host}:{opt.port}\n',
            file=sys.stderr)
        print('', file=sys.stderr)
        print('Check, wether the initvm is actually running.', file=sys.stderr)
        print('try `elbe initvm start`', file=sys.stderr)
        sys.exit(10)
    except socket.error:
        print(
            f'Failed to connect to Soap server {opt.host}:{opt.port}\n',
            file=sys.stderr)
        print('', file=sys.stderr)
        print(
            'Check, wether the Soap Server is running inside the initvm',
            file=sys.stderr)
        print("try 'elbe initvm attach'", file=sys.stderr)
        sys.exit(11)
    except BadStatusLine:
        print(
            f'Failed to connect to Soap server {opt.host}:{opt.port}\n',
            file=sys.stderr)
        print('', file=sys.stderr)
        print('Check, wether the initvm is actually running.', file=sys.stderr)
        print(
            "try 'elbe initvm --directory /path/to/initvm start'",
            file=sys.stderr)
        sys.exit(12)

    # Check whether subcommand exists
    try:
        action = RepoAction(args[0])
    except KeyError:
        print('elbe prjrepo - unknown subcommand', file=sys.stderr)
        RepoAction.print_actions()
        sys.exit(22)

    # Execute command
    try:
        action.execute(control, opt, args[1:])
    except WebFault as e:
        print('Server returned an error:', file=sys.stderr)
        print('', file=sys.stderr)
        if hasattr(e.fault, 'faultstring'):
            print(e.fault.faultstring, file=sys.stderr)
        else:
            print(e, file=sys.stderr)
        sys.exit(5)
