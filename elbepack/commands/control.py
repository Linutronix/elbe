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

import socket
import sys

from optparse import OptionParser
from suds.client import Client

from elbepack.soapclient import ClientAction

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
    (opt,args) = oparser.parse_args (sys.argv)
    args = args[2:]

    wsdl = "http://" + opt.host + ":" + str(opt.port) + "/soap/?wsdl"
    control = None

    try:
        control = Client (wsdl)
    except socket.error as e:
        print e, wsdl
        return

    if len(args) < 1:
        print 'elbe control - no subcommand given'
        ClientAction.print_actions ()
        return

    try:
        ClientAction (args[0]).execute (control, opt.user, opt.passwd, args[1:])
    except KeyError:
        print 'elbe control - unknown subcommand'
        ClientAction.print_actions ()
        return
