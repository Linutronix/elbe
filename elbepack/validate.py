# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2014-2017 Linutronix GmbH

import os
import sys

from lxml import etree
from lxml.etree import XMLParser, parse

from elbepack.treeutils import dbsfed_schema


def error_log_to_strings(error_log):
    errors = []
    uses_xinclude = False
    uses_norecommend = False

    for err in error_log:
        errors.append(f'{err.filename}:{err.line} error {err.message}')
        if 'http://www.w3.org/2003/XInclude' in err.message:
            uses_xinclude = True
        if 'norecommend' in err.message:
            uses_norecommend = True

    if uses_xinclude:
        errors.append('\nThere are XIncludes in the XML file. '
                      "Run 'elbe preprocess' first!\n")
    if uses_norecommend:
        errors.append('\nThe XML file uses <norecommend />. '
                      'This function was broken all the time and did the '
                      'opposite. If you want to retain the original '
                      'behaviour, please specify <install-recommends /> !\n')
    return errors


def validate_xml(fname):
    if os.path.getsize(fname) > (1 << 30):
        return [f'{fname} is greater than 1 GiB. '
                'Elbe does not support files of this size.']

    parser = XMLParser(huge_tree=True)
    schema = dbsfed_schema()

    try:
        xml = parse(fname, parser=parser)

        if schema.validate(xml):
            return validate_xml_content(xml)
    except etree.XMLSyntaxError:
        return ['XML Parse error\n' + str(sys.exc_info()[1])]
    except BaseException:
        return ['Unknown Exception during validation\n' +
                str(sys.exc_info()[1])]

    # We have errors, return them in string form...
    return error_log_to_strings(schema.error_log)


def validate_xml_content(xml):
    errors = []

    # Check if https can be safely used
    #
    # If apt-transport-https or ca-certificates is included in bootstrap,
    # we are probably fine
    bootstrap_include = xml.findtext('./target/debootstrap/include', '')
    if ('apt-transport-https' not in bootstrap_include
       and 'ca-certificates' not in bootstrap_include):

        # Check if primary mirror is using https
        primary_proto = xml.findtext('./project/mirror/primary_proto', '')
        is_primary_proto_https = (primary_proto.lower() == 'https')

        # Check if any additional mirror is using https
        has_https_urls = False
        for url in xml.findall('./project/mirror/url-list/url'):
            b = url.findtext('binary', '').lower()
            s = url.findtext('source', '').lower()
            if b.startswith('https') or s.startswith('https'):
                has_https_urls = True
                break

        if is_primary_proto_https or has_https_urls:
            errors.append('\nThe XML contains an HTTPS mirror. '
                          'Use debootstrap/include '
                          'to make apt-transport-https (stretch and older) '
                          'or ca-certificates (buster and newer) available '
                          'in debootstrap.\n')

    return errors
