# ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (C) 2017  Linutronix GmbH
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

import sys
from lxml import etree
from lxml.etree import XMLParser,parse

class XMLPreprocessError(Exception):
    def __init__ (self, message):
        Exception.__init__(self, message)

def xmlpreprocess(fname, output):
    schema_file = "https://www.linutronix.de/projects/Elbe/dbsfed.xsd"
    parser = XMLParser(huge_tree=True)
    schema_tree = etree.parse(schema_file)
    schema = etree.XMLSchema(schema_tree)

    try:
        xml = parse(fname,parser=parser)
        xml.xinclude()

        if schema.validate(xml):
            xml.write(output, encoding="UTF-8", pretty_print=True, compression=9)
            return

    except etree.XMLSyntaxError:
        raise XMLPreprocessError("XML Parse error\n" + str(sys.exc_info()[1]))
    except:
        XMLPreprocessError("Unknown Exception during validation\n" + str(sys.exc_info()[1]))

    # We have errors, return them in string form...
    errors = []
    for err in schema.error_log:
        errors.append("%s:%d error %s" % (err.filename, err.line, err.message))

    raise XMLPreprocessError(errors)
