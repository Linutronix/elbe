# ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (c) 2017 Benedikt Spranger <b.spranger@linutronix.de>
# Copyright (c) 2017 Manuel Traut <manut@linutronix.de>
# Copyright (c) 2018 Torben Hohn <torbenh@linutronix.de>
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import print_function

import sys
from tempfile import NamedTemporaryFile
from optparse import OptionGroup

from lxml import etree
from lxml.etree import XMLParser, parse

from elbepack.archivedir import ArchivedirError, combinearchivedir
from elbepack.directories import elbe_exe
from elbepack.shellhelper import command_out_stderr, CommandError
from elbepack.validate import error_log_to_strings

# list of sections that are allowed to exists multiple times before
# preprocess and that childrens are merge into one section during preprocess
mergepaths = ['//target/finetuning',
              '//target/pkg-list',
              '//project/buildimage/pkg-list']


class XMLPreprocessError(Exception):
    pass

def preprocess_pgp_key(xml):

    for key in xml.iterfind('project/mirror/url-list/url/key'):
        print("[WARN] <key>%s</key> is deprecated.  You should use raw-key instead." % key.text)
        try:
            keyurl = key.text.strip().replace('LOCALMACHINE', '10.0.2.2')
            myKey = urllib2.urlopen(keyurl).read()
            key.tag = "raw-key"
            key.text = "\n%s\n" % myKey
        except urllib2.HTTPError as E:
            raise XMLPreprocessError("Invalid PGP Key URL in <key> tag: %s" % keyurl)

def xmlpreprocess(fname, output, variants=None):

    # pylint: disable=too-many-locals
    # pylint: disable=too-many-branches

    # first convert variants to a set
    if not variants:
        variants = set([])
    else:
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
                tag_variants = set(tag.attrib['variant'].split(','))

                # check if tag_variants intersects with
                # active variants.
                intersect = variants.intersection(tag_variants)

                if intersect:
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
            mergenodes = xml.xpath(mergepath)

            # if there is just one section of a type
            # or no section, nothing needs to be done
            if len(mergenodes) < 2:
                continue

            # append all childrens of section[1..n] to section[0] and delete
            # section[1..n]
            for section in mergenodes[1:]:
                for c in section.getchildren():
                    mergenodes[0].append(c)
                section.getparent().remove(section)

        # handle archivedir elements
        xml = combinearchivedir(xml)

        # Change public PGP url key to raw key
        preprocess_pgp_key(xml)

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
    raise XMLPreprocessError("\n".join(error_log_to_strings(schema.error_log)))


class PreprocessWrapper(object):    # pylint: disable=too-few-public-methods
    def __init__(self, xmlfile, opt):
        self.xmlfile = xmlfile
        self.outxml = None
        self.options = ""

        if opt.variant:
            self.options += ' --variants "%s"' % opt.variant

    def __enter__(self):
        self.outxml = NamedTemporaryFile(prefix='elbe', suffix='xml')

        cmd = '%s preprocess %s -o %s %s' % (elbe_exe,
                                             self.options,
                                             self.outxml.name,
                                             self.xmlfile)
        ret, _, err = command_out_stderr(cmd)
        if ret != 0:
            print("elbe preprocess failed.", file=sys.stderr)
            print(err, file=sys.stderr)
            raise CommandError(cmd, ret)

        return self

    def __exit__(self, _typ, _value, _traceback):
        self.outxml = None

    @staticmethod
    def add_options(oparser):
        # import it here because of cyclic imports
        from elbepack.commands.preprocess import add_pass_through_options

        group = OptionGroup(oparser,
                            'Elbe preprocess options',
                            'Options passed through to invocation of '
                            '"elbe preprocess"')
        add_pass_through_options(group)
        oparser.add_option_group(group)

    @property
    def preproc(self):
        return self.outxml.name
