#!/usr/bin/env python
#
# ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (C) 2014  Linutronix GmbH
#
# This file is part of ELBE.
#
# ELBE is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# ELBE is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with ELBE.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import print_function

import socket
import sys

from optparse import OptionParser
from suds import WebFault

from elbepack.soapclient import ClientAction, ElbeSoapClient

def run_command (argv):
    oparser = OptionParser (usage="usage: elbe control [options] <command>")

    oparser.add_option ("--host", dest="host", default="localhost",
                        help="ip or hostname of elbe-daemon")

    oparser.add_option ("--port", dest="port", default="8080",
                        help="port of soap itf on elbe-daemon")

    oparser.add_option ("--pass", dest="passwd", default="foo",
                        help="password (default is foo)")

    oparser.add_option ("--user", dest="user", default="root",
                        help="username (default is root)")

    oparser.add_option ("--debug", action="store_true",
                        dest="debug", default=False,
                        help="enable debug mode")
    (opt,args) = oparser.parse_args (sys.argv)
    args = args[2:]

    if len(args) < 1:
        print ('elbe control - no subcommand given', file=sys.stderr)
        ClientAction.print_actions ()
        return

    try:
        control = ElbeSoapClient (opt.host, opt.port, opt.user, opt.passwd, debug=opt.debug)
    except socket.error as e:
        print ("Failed to connect to Soap server %s:%s\n" % (opt.host, opt.port), file=sys.stderr)
        sys.exit(10)


    try:
        action = ClientAction (args[0])
    except KeyError:
        print ('elbe control - unknown subcommand', file=sys.stderr)
        ClientAction.print_actions ()
        sys.exit(20)

    try:
        action.execute (control, args[1:])
    except WebFault as e:
        print ('Soap Exception', file=sys.stderr)
        print (e, file=sys.stderr)
        sys.exit(5)
