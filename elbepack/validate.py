# ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (C) 2013  Linutronix GmbH
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

import os
import sys
import elbepack
from lxml import etree
from optparse import OptionParser

def validate_xml(fname):
    schema_file = os.path.join( elbepack.__path__[0], "dbsfed.xsd" )
    schema_tree = etree.parse(schema_file)
    schema = etree.XMLSchema(schema_tree)

    try:
        xml=etree.parse(fname)

        if schema.validate(xml):
            return True
    except etree.XMLSyntaxError:
        print "XML Parse error"
        print str(sys.exc_info()[1])
        return False
    except:
        print "Unknown Exception during validation"
        print sys.exc_info()[1]
        return False

    # We have an error... lets print the log.

    for err in schema.error_log:
        print "%s:%d error %s" % (err.filename, err.line, err.message)

    return False

def run_command( argv ):
    oparser = OptionParser( usage="usage: %prog validate <xmlfile>")
    (opt,args) = oparser.parse_args(argv)

    if len(args) != 1:
        print "Wrong number of arguments"
        oparser.print_help()
        sys.exit(20)

    if validate_xml(args[0]):
        sys.exit(0)
    else:
        print "validation failed"
        sys.exit(20)


