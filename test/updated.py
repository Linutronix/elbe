#!/usr/bin/env python3

# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2014, 2017 Linutronix GmbH

import argparse
import sys
import threading
import time
from wsgiref.simple_server import make_server

from spyne import Application, ServiceBase, rpc
from spyne.model.primitive import String
from spyne.protocol.soap import Soap11
from spyne.server.wsgi import WsgiApplication

from suds.client import Client


class MonitorService (ServiceBase):
    @rpc(String)
    def msg(self, m):
        print(m)


class MonitorThread (threading.Thread):
    def __init__(self, port):
        super().__init__(name='MonitorThread')
        self.port = port
        self.server = None

    def run(self):
        print('monitor ready :%s' % (self.port))
        application = Application([MonitorService], 'monitor',
                                  in_protocol=Soap11(validator='lxml'),
                                  out_protocol=Soap11())
        wsgi_application = WsgiApplication(application)
        self.server = make_server('', int(self.port), wsgi_application)
        self.server.serve_forever()


def shutdown(mon):
    if mon.server:
        mon.server.shutdown()

    mon.join()
    sys.exit(0)


aparser = argparse.ArgumentParser()

aparser.add_argument('--debug', dest='debug', action='store_true',
                     default=False, help='run in debug mode')

aparser.add_argument('--target', dest='target', default='localhost',
                     help='ip or hostname of target', type='string')

aparser.add_argument('--port', dest='port', default='8080',
                     help='port of updated on target', type='string')

aparser.add_argument('--listen', dest='host', default='localhost',
                     help='interface ip', type='string')

aparser.add_argument('--monitorport', dest='monitorport', default='8087',
                     help='port used for update monitor', type='string')

args = aparser.parse_args(sys.argv)

if args.debug:
    import logging
    logging.basicConfig(level=logging.INFO)
    logging.getLogger('suds.client').setLevel(logging.DEBUG)

wsdl = 'http://' + args.target + ':' + args.port + '/?wsdl'
try:
    control = Client(wsdl)
except BaseException:
    print(wsdl, 'not reachable')
    sys.exit(1)

monitor = MonitorThread(args.monitorport)
monitor.start()

time.sleep(1)  # hack to ensure that monitor server was started

try:
    monitor_wsdl = 'http://' + args.host + ':' + args.monitorport + '/?wsdl'
    control.service.register_monitor(monitor_wsdl)
except BaseException:
    print("monitor couldn\'t be registered (port already in use?)")
    shutdown(monitor)

while 1:
    s = control.service.list_snapshots()
    snapshots = []
    try:
        snapshots = s.split(',')

        print('select snapshot:')
        i = 0
        for s in snapshots:
            if s:
                print('  [%d] %s' % (i, s))
            i = i + 1
    except BaseException:
        print('no snapshots available')

    sys.stdout.write('% ')
    sys.stdout.flush()

    try:
        n = int(input())
        print(control.service.apply_snapshot(snapshots[n]))
    except BaseException:
        shutdown(monitor)
