# ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (c) 2014-2015 Torben Hohn <torbenh@linutronix.de>
# Copyright (c) 2017 Benedikt Spranger <b.spranger@linutronix.de>
# Copyright (c) 2017 Manuel Traut <manut@linutronix.de>
#
# SPDX-License-Identifier: GPL-3.0-or-later

import sys
from lxml import etree
from lxml.etree import XMLParser, parse


def validate_xml(fname):
    schema_file = "https://www.linutronix.de/projects/Elbe/dbsfed.xsd"
    parser = XMLParser(huge_tree=True)
    schema_tree = etree.parse(schema_file)
    schema = etree.XMLSchema(schema_tree)

    try:
        xml = parse(fname, parser=parser)

        if schema.validate(xml):
            return []
    except etree.XMLSyntaxError:
        return ["XML Parse error\n" + str(sys.exc_info()[1])]
    except BaseException:
        return ["Unknown Exception during validation\n" +
                str(sys.exc_info()[1])]

    # We have errors, return them in string form...
    errors = []
    uses_xinclude = False

    for err in schema.error_log:
        errors.append("%s:%d error %s" % (err.filename, err.line, err.message))
        if "http://www.w3.org/2003/XInclude" in err.message:
            uses_xinclude = True

    if uses_xinclude:
        errors.append("\nThere are XIncludes in the XML file. "
                      "Run 'elbe preprocess' first!\n")

    return errors
