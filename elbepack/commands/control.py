# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2014-2017 Linutronix GmbH

import socket
import sys
from http.client import BadStatusLine
from optparse import OptionGroup, OptionParser
from urllib.error import URLError

from suds import WebFault

from elbepack.config import cfg
from elbepack.elbexml import ValidationMode
from elbepack.soapclient import ClientAction, ElbeSoapClient


def run_command(argv):

    oparser = OptionParser(usage='usage: elbe control [options] <command>')

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
        help='How many times to retry the connection to the server before '
             'giving up (default is 10 times, yielding 10 seconds).')

    oparser.add_option(
        '--build-bin',
        action='store_true',
        dest='build_bin',
        default=False,
        help='Build binary repository CDROM, for exact reproduction.')

    oparser.add_option('--build-sources', action='store_true',
                       dest='build_sources', default=False,
                       help='Build source CDROM')

    oparser.add_option(
        '--skip-pbuilder',
        action='store_true',
        dest='skip_pbuilder',
        default=False,
        help="skip pbuilder section of XML (don't build packages)")

    oparser.add_option('--output',
                       dest='output', default=None,
                       help='Output files to <directory>')

    oparser.add_option('--matches', dest='matches', default=False,
                       help='Select files based on wildcard expression.')

    oparser.add_option('--pbuilder-only', action='store_true',
                       dest='pbuilder_only', default=False,
                       help='Only list/download pbuilder Files')

    oparser.add_option('--profile', dest='profile', default='',
                       help='Make pbuilder commands build the specified profile')

    oparser.add_option('--cross', dest='cross', default=False,
                       action='store_true',
                       help='Creates an environment for crossbuilding if '
                            'combined with create. Combined with build it'
                            ' will use this environment.')

    oparser.add_option('--no-ccache', dest='noccache', default=False,
                       action='store_true',
                       help="Deactivates the compiler cache 'ccache'")

    oparser.add_option('--ccache-size', dest='ccachesize', default='10G',
                       action='store', type='string',
                       help='set a limit for the compiler cache size '
                            '(should be a number followed by an optional '
                            'suffix: k, M, G, T. Use 0 for no limit.)')

    devel = OptionGroup(
        oparser,
        'options for elbe developers',
        "Caution: Don't use these options in a productive environment")
    devel.add_option('--skip-urlcheck', action='store_true',
                     dest='url_validation', default=ValidationMode.CHECK_ALL,
                     help='Skip URL Check inside initvm')

    devel.add_option('--debug', action='store_true',
                     dest='debug', default=False,
                     help='Enable debug mode.')

    (opt, args) = oparser.parse_args(argv)

    if not args:
        print('elbe control - no subcommand given', file=sys.stderr)
        ClientAction.print_actions()
        return

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
        print('Check, whether the initvm is actually running.', file=sys.stderr)
        print("try 'elbe initvm start'", file=sys.stderr)
        sys.exit(13)
    except socket.error:
        print(
            f'Failed to connect to Soap server {opt.host}:{opt.port}\n',
            file=sys.stderr)
        print('', file=sys.stderr)
        print(
            'Check, whether the Soap Server is running inside the initvm',
            file=sys.stderr)
        print("try 'elbe initvm attach'", file=sys.stderr)
        sys.exit(14)
    except BadStatusLine:
        print(
            f'Failed to connect to Soap server {opt.host}:{opt.port}\n',
            file=sys.stderr)
        print('', file=sys.stderr)
        print('Check, whether the initvm is actually running.', file=sys.stderr)
        print("try 'elbe initvm start'", file=sys.stderr)
        sys.exit(15)

    try:
        action = ClientAction(args[0])
    except KeyError:
        print('elbe control - unknown subcommand', file=sys.stderr)
        ClientAction.print_actions()
        sys.exit(25)

    try:
        action.execute(control, opt, args[1:])
    except WebFault as e:
        print('Server returned error:', file=sys.stderr)
        print('', file=sys.stderr)
        if hasattr(e.fault, 'faultstring'):
            print(e.fault.faultstring, file=sys.stderr)
        else:
            print(e, file=sys.stderr)
        sys.exit(6)
