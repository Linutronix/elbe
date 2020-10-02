# ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (c) 2017 Philipp Arras <philipp.arras@linutronix.de>
# Copyright (c) 2017 Kurt Kanzenbach <kurt@linutronix.de>
# Copyright (c) 2017 Manuel Traut <manut@linutronix.de>
#
# SPDX-License-Identifier: GPL-3.0-or-later

import socket
import sys

from http.client import BadStatusLine
from optparse import (OptionParser, OptionGroup)
from urllib.error import URLError

from suds import WebFault

from elbepack.soapclient import RepoAction, ElbeSoapClient
from elbepack.version import elbe_version
from elbepack.config import cfg


def run_command(argv):

    # pylint: disable=too-many-statements

    oparser = OptionParser(usage="usage: elbe prjrepo [options] <command>")

    oparser.add_option("--host", dest="host", default=cfg['soaphost'],
                       help="Ip or hostname of elbe-daemon.")

    oparser.add_option("--port", dest="port", default=cfg['soapport'],
                       help="Port of soap itf on elbe-daemon.")

    oparser.add_option("--pass", dest="passwd", default=cfg['elbepass'],
                       help="Password (default is foo).")

    oparser.add_option("--user", dest="user", default=cfg['elbeuser'],
                       help="Username (default is root).")

    oparser.add_option(
        "--retries",
        dest="retries",
        default="10",
        help="How many times to retry the connection to the server before\
                giving up (default is 10 times, yielding 10 seconds).")

    devel = OptionGroup(
        oparser,
        "options for elbe developers",
        "Caution: Don't use these options in a productive environment")
    devel.add_option("--debug", action="store_true",
                     dest="debug", default=False,
                     help="Enable debug mode.")

    devel.add_option("--ignore-version-diff", action="store_true",
                     dest="ignore_version", default=False,
                     help="allow different elbe version on host and initvm")
    oparser.add_option_group(devel)

    (opt, args) = oparser.parse_args(argv)

    if len(args) < 1:
        print("elbe prjrepo - no subcommand given", file=sys.stderr)
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
    except URLError as e:
        print("Failed to connect to Soap server %s:%s\n" %
              (opt.host, opt.port), file=sys.stderr)
        print("", file=sys.stderr)
        print("Check, wether the initvm is actually running.", file=sys.stderr)
        print("try `elbe initvm start`", file=sys.stderr)
        sys.exit(10)
    except socket.error as e:
        print("Failed to connect to Soap server %s:%s\n" %
              (opt.host, opt.port), file=sys.stderr)
        print("", file=sys.stderr)
        print(
            "Check, wether the Soap Server is running inside the initvm",
            file=sys.stderr)
        print("try 'elbe initvm attach'", file=sys.stderr)
        sys.exit(10)
    except BadStatusLine as e:
        print("Failed to connect to Soap server %s:%s\n" %
              (opt.host, opt.port), file=sys.stderr)
        print("", file=sys.stderr)
        print("Check, wether the initvm is actually running.", file=sys.stderr)
        print(
            "try 'elbe initvm --directory /path/to/initvm start'",
            file=sys.stderr)
        sys.exit(10)

    # Check Elbe version
    try:
        v_server = control.service.get_version()
        if v_server != elbe_version:
            print("elbe v%s is used in initvm, this is not compatible witha"
                  "elbe v%s that is used on this machine. Please install same "
                  "versions of elbe in initvm and on your machine." % (
                      v_server, elbe_version),
                  file=sys.stderr)

            if not opt.ignore_version:
                sys.exit(20)
    except AttributeError:
        print("the elbe installation inside the initvm doesn't provide a \
get_version interface. Please create a new initvm or upgrade \
elbe inside the existing initvm.", file=sys.stderr)
        if not opt.ignore_version:
            sys.exit(20)

    # Check whether subcommand exists
    try:
        action = RepoAction(args[0])
    except KeyError:
        print("elbe prjrepo - unknown subcommand", file=sys.stderr)
        RepoAction.print_actions()
        sys.exit(20)

    # Execute command
    try:
        action.execute(control, opt, args[1:])
    except WebFault as e:
        print("Server returned an error:", file=sys.stderr)
        print("", file=sys.stderr)
        if hasattr(e.fault, 'faultstring'):
            print(e.fault.faultstring, file=sys.stderr)
        else:
            print(e, file=sys.stderr)
        sys.exit(5)
