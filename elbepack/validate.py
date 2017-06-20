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

import sys
from lxml import etree
from lxml.etree import XMLParser,parse

def validate_xml(fname):
    schema_file = "https://www.linutronix.de/projects/Elbe/dbsfed.xsd"
    parser = XMLParser(huge_tree=True)
    schema_tree = etree.parse(schema_file)
    schema = etree.XMLSchema(schema_tree)

    try:
        xml = parse(fname,parser=parser)

        if schema.validate(xml):
            return []
    except etree.XMLSyntaxError:
        return ["XML Parse error\n" + str(sys.exc_info()[1])]
    except:
        return ["Unknown Exception during validation\n" + str(sys.exc_info()[1])]

    # We have errors, return them in string form...
    errors = []
    for err in schema.error_log:
        errors.append ("%s:%d error %s" % (err.filename, err.line, err.message))

    return errors

