#!/usr/bin/python

import soaplib
import sys
import threading

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
    def __init__ (self, host, port):
        threading.Thread.__init__ (self)
        self.host = host
        self.port = port

    def run (self):
        print "monitor ready %s:%s" % (self.host, self.port)
        server = make_server (self.host, int (self.port), MonitorService ())
        server.serve_forever ()


oparser = OptionParser (usage="usage: %prog [options]")

oparser.add_option ("--target", dest="target",
                    help="ip or hostname of target")

oparser.add_option ("--port", dest="port",
                    help="port of updated on target")

oparser.add_option ("--listen", dest="host",
                    help="interface ip")

oparser.add_option ("--monitorport", dest="monitorport",
                    help="port used for update monitor")

(opt,args) = oparser.parse_args (sys.argv)

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

monitor = MonitorThread (host, monitorport)
monitor.start ()

monitor_wsdl = "http://" + host + ":" + monitorport + "/?wsdl"
control.service.register_monitor (monitor_wsdl)

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
n = int (raw_input ())

print control.service.apply_snapshot (snapshots [n])

sys.exit (0)
