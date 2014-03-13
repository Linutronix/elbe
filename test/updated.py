#!/usr/bin/env python

# there are warnings raised by python-soaplib
import warnings
warnings.filterwarnings("ignore", category=FutureWarning)

import soaplib
import sys
import threading
import time

from optparse import OptionParser
from soaplib.service import soapmethod
from soaplib.wsgi_soap import SimpleWSGISoapApp
from soaplib.serializers.primitive import String, Array
from suds.client import Client
from wsgiref.simple_server import make_server

class MonitorService (SimpleWSGISoapApp):
    @soapmethod (String)
    def msg (self, m):
        print m

class MonitorThread (threading.Thread):
    def __init__ (self, port):
        threading.Thread.__init__ (self)
        self.port = port
        self.server = None

    def run (self):
        print "monitor ready :%s" % (self.port)
        self.server = make_server ("", int(self.port), MonitorService())
        self.server.serve_forever ()

def shutdown (monitor):
    if monitor.server:
        monitor.server.shutdown ()

    monitor.join ()
    sys.exit (0)

oparser = OptionParser (usage="usage: %prog [options]")

oparser.add_option ("--debug", dest="debug", action="store_true",
                    default=False,
                    help="run in debug mode")

oparser.add_option ("--target", dest="target",
                    help="ip or hostname of target")

oparser.add_option ("--port", dest="port",
                    help="port of updated on target")

oparser.add_option ("--listen", dest="host",
                    help="interface ip")

oparser.add_option ("--monitorport", dest="monitorport",
                    help="port used for update monitor")

(opt,args) = oparser.parse_args (sys.argv)

if opt.debug:
    import logging
    logging.basicConfig (level=logging.INFO)
    logging.getLogger ('suds.client').setLevel (logging.DEBUG)

if not opt.target:
    target = "localhost"
else:
    target = opt.target

if not opt.port:
    port = "8088"
else:
    port = str (opt.port)

if not opt.monitorport:
    monitorport = "8087"
else:
    monitorport = opt.monitorport

if not opt.host:
    host = "localhost"
else:
    host = opt.host

wsdl = "http://" + target + ":" + port + "/?wsdl"
try:
    control = Client (wsdl)
except:
    print wsdl, "not reachable"
    sys.exit (1)

monitor = MonitorThread (monitorport)
monitor.start ()

time.sleep (1) # hack to ensure that monitor server was started

try:
    monitor_wsdl = "http://" + host + ":" + monitorport + "/?wsdl"
    control.service.register_monitor (monitor_wsdl)
except:
    print "monitor couldn't be registered (port already in use?)"
    shutdown (monitor)

while 1:
    s = control.service.list_snapshots ()
    snapshots = s.split (',')

    print "select snapshot:"
    i = 0
    for s in snapshots:
        if s:
            print "  [%d] %s" % (i, s)
        i = i + 1

    sys.stdout.write ("% ")
    sys.stdout.flush ()

    try:
        n = int (raw_input ())
        print control.service.apply_snapshot (snapshots [n])
    except:
        shutdown (monitor)
