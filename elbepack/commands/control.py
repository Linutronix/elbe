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
from suds import WebFault

from elbepack.soapclient import ClientAction, ElbeSoapClient

import logging
if False:
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

    if len(args) < 1:
        print 'elbe control - no subcommand given'
        ClientAction.print_actions ()
        return

    try:
        control = ElbeSoapClient (opt.host, opt.port, opt.user, opt.passwd)
    except socket.error as e:
        print "Failed to connect to Soap server %s:%d\n" % (opt.host, opt.port)
        return


    try:
        action = ClientAction (args[0])
    except KeyError:
        print 'elbe control - unknown subcommand'
        ClientAction.print_actions ()
        return

    try:
        action.execute (control, args[1:])
    except WebFault as e:
        print "Soap Exception"
        print e
        return
