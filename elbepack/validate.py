# ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (c) 2014-2015 Torben Hohn <torbenh@linutronix.de>
# Copyright (c) 2017 Benedikt Spranger <b.spranger@linutronix.de>
# Copyright (c) 2017 Manuel Traut <manut@linutronix.de>
#
# SPDX-License-Identifier: GPL-3.0-or-later

import os
import sys

from lxml import etree
from lxml.etree import XMLParser, parse


def validate_xml(fname):
    if os.path.getsize(fname) > (1 << 30):
        return ["%s is greater than 1 GiB. "
                "Elbe does not support files of this size." % fname]

    schema_file = "https://www.linutronix.de/projects/Elbe/dbsfed.xsd"
    parser = XMLParser(huge_tree=True)
    schema_tree = etree.parse(schema_file)
    schema = etree.XMLSchema(schema_tree)

    try:
        xml = parse(fname, parser=parser)

        if schema.validate(xml):
            return validate_xml_content(xml)
    except etree.XMLSyntaxError:
        return ["XML Parse error\n" + str(sys.exc_info()[1])]
    except BaseException:
        return ["Unknown Exception during validation\n" +
                str(sys.exc_info()[1])]

    # We have errors, return them in string form...
    errors = []
    uses_xinclude = False
    uses_norecommend = False

    for err in schema.error_log:
        errors.append("%s:%d error %s" % (err.filename, err.line, err.message))
        if "http://www.w3.org/2003/XInclude" in err.message:
            uses_xinclude = True
        if "norecommend" in err.message:
            uses_norecommend = True

    if uses_xinclude:
        errors.append("\nThere are XIncludes in the XML file. "
                      "Run 'elbe preprocess' first!\n")
    if uses_norecommend:
        errors.append("\nThe XML file uses <norecommend />. "
                      "This function was broken all the time and did the "
                      "opposite. If you want to retain the original "
                      "behaviour, please specify <install-recommends /> !\n")

    return errors


def validate_xml_content(xml):
    errors = []

    dbsv = xml.find("/target/debootstrapvariant")

    if (dbsv is not None and "minbase" in dbsv.text
            and "gnupg" not in dbsv.get("includepkgs", "")
            and xml.find("/project/mirror/url-list/url/key") is not None):

        errors.append("\nThe XML contains a custom mirror key. "
                      "Use debootstrapvariant's attribute includepkgs "
                      "to make gnupg available in debootstrap.\n")

    primary_proto = xml.findtext("/project/mirror/primary_proto", "")
    https = (primary_proto.lower() == "https")

    if (not https
        and (dbsv is None
             or "apt-transport-https" not in dbsv.get("includepkgs", ""))):
        for url in xml.findall("/project/mirror/url-list/url"):
            b = url.findtext("binary", "")
            s = url.findtext("source", "")
            if b.startswith("https") or s.startswith("https"):
                errors.append("\nThe XML contains an HTTPS mirror. "
                              "Use debootstrapvariant's attribute includepkgs "
                              "to make apt-transport-https available in "
                              "debootstrap.\n")
                break

    return errors
