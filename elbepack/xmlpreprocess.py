# ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (c) 2017 Benedikt Spranger <b.spranger@linutronix.de>
# Copyright (c) 2017 Manuel Traut <manut@linutronix.de>
#
# SPDX-License-Identifier: GPL-3.0-or-later

import sys
import re
from lxml import etree
from lxml.etree import XMLParser, parse
from elbepack.archivedir import ArchivedirError, combinearchivedir

# list of sections that are allowed to exists multiple times before
# preprocess and that childrens are merge into one section during preprocess
mergepaths = ['//target/finetuning',
              '//target/pkg-list',
              '//project/buildimage/pkg-list']


class XMLPreprocessError(Exception):
    pass


def xmlpreprocess(fname, output, variants=[]):

    # pylint: disable=too-many-locals
    # pylint: disable=too-many-branches

    # first convert variants to a set
    variants = set(variants)

    schema_file = "https://www.linutronix.de/projects/Elbe/dbsfed.xsd"
    parser = XMLParser(huge_tree=True)
    schema_tree = etree.parse(schema_file)
    schema = etree.XMLSchema(schema_tree)

    try:
        xml = parse(fname, parser=parser)
        xml.xinclude()

        # Variant management
        # check all nodes for variant field, and act accordingly.
        # The result will not contain any variant attributes anymore.
        rmlist = []
        for tag in xml.iter('*'):
            if 'variant' in tag.attrib:
                tag_variants = set (tag.attrib['variant'].split(','))

                # check if tag_variants intersects with
                # active variants.
                intersect = variants.intersection(tag_variants)

                if len(intersect):
                    # variant is wanted, keep it and remove the variant
                    # attribute
                    tag.attrib.pop('variant')
                else:
                    # tag has a variant attribute but the variant was not
                    # specified: remove the tag delayed
                    rmlist.append(tag)

        for tag in rmlist:
            tag.getparent().remove(tag)

        # if there are multiple sections because of sth like '<finetuning
        # variant='A'> ...  and <finetuning variant='B'> and running preprocess
        # with --variant=A,B the two sections need to be merged
        #
        # Use xpath expressions to identify mergeable sections.
        for mergepath in mergepaths:
            mergenodes = xml.xpath (mergepath)

            # if there is just one section of a type
            # or no section, nothing needs to be done
            if len(mergenodes) < 2:
                continue

            # append all childrens of section[1..n] to section[0] and delete
            # section[1..n]
            for section in mergenodes[1:]:
                for c in section.getchildren():
                    mergenodes[0].append (c)
                section.getparent().remove(section)

        # handle archivedir elements
        xml = combinearchivedir(xml)

        if schema.validate(xml):
            # if validation succedes write xml file
            xml.write(
                output,
                encoding="UTF-8",
                pretty_print=True,
                compression=9)
            # the rest of the code is exception and error handling
            return

    except etree.XMLSyntaxError:
        raise XMLPreprocessError("XML Parse error\n" + str(sys.exc_info()[1]))
    except ArchivedirError:
        raise XMLPreprocessError("<archivedir> handling failed\n" +
                                     str(sys.exc_info()[1]))
    except BaseException:
        raise XMLPreprocessError(
            "Unknown Exception during validation\n" + str(sys.exc_info()[1]))

    # We have errors, return them in string form...
    errors = []
    for err in schema.error_log:
        errors.append("%s:%d error %s" % (err.filename, err.line, err.message))

    raise XMLPreprocessError(errors)
