# ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (c) 2017 Benedikt Spranger <b.spranger@linutronix.de>
# Copyright (c) 2017 Manuel Traut <manut@linutronix.de>
# Copyright (c) 2018 Torben Hohn <torbenh@linutronix.de>
#
# SPDX-License-Identifier: GPL-3.0-or-later

import os
import re
import sys

from tempfile import NamedTemporaryFile
from optparse import OptionGroup
from itertools import islice
from urllib.error import HTTPError
from urllib.request import urlopen

from lxml import etree
from lxml.etree import XMLParser, parse, Element

from elbepack.archivedir import ArchivedirError, combinearchivedir
from elbepack.config import cfg
from elbepack.directories import elbe_exe
from elbepack.shellhelper import command_out_stderr, CommandError
from elbepack.isooptions import iso_option_valid
from elbepack.validate import error_log_to_strings

# list of sections that are allowed to exists multiple times before
# preprocess and that childrens are merge into one section during preprocess
mergepaths = ['//target/finetuning',
              '//target/pkg-list',
              '//project/buildimage/pkg-list']


class XMLPreprocessError(Exception):
    pass


def preprocess_pgp_key(xml):

    for key in xml.iterfind('.//mirror/url-list/url/key'):
        print("[WARN] <key>%s</key> is deprecated. "
              "You should use raw-key instead." % key.text)
        try:
            keyurl = key.text.strip().replace('LOCALMACHINE', 'localhost')
            myKey = urlopen(keyurl).read().decode('ascii')
            key.tag = "raw-key"
            key.text = "\n%s\n" % myKey
        except HTTPError:
            raise XMLPreprocessError("Invalid PGP Key URL in <key> tag: %s" %
                                     keyurl)


def preprocess_iso_option(xml):

    src_opts = xml.find(".//src-cdrom/src-opts")
    if src_opts is None:
        return

    strict = ("strict" in src_opts.attrib
              and src_opts.attrib["strict"] == "true")

    for opt in src_opts.iterfind("./*"):
        valid = iso_option_valid(opt.tag, opt.text)
        if valid is True:
            continue

        tag = '<%s>%s</%s>' % (opt.tag, opt.text, opt.tag)

        if valid is False:
            violation = "Invalid ISO option %s" % tag
        elif isinstance(valid, int):
            violation = ("Option %s will be truncated by %d characters" %
                         (tag, valid))
        elif isinstance(valid, str):
            violation = ("Character '%c' (%d) in ISO option %s "
                         "violated ISO-9660" %
                         (valid, ord(valid[0]), tag))
        if strict:
            raise XMLPreprocessError(violation)
        print("[WARN] %s" % violation)


def preprocess_initvm_ports(xml):
    "Filters out the default port forwardings to prevent qemu conflict"

    for forward in xml.iterfind('initvm/portforwarding/forward'):
        prot = forward.find('proto')
        benv = forward.find('buildenv')
        host = forward.find('host')
        if prot is None or benv is None or host is None:
            continue
        if prot.text == 'tcp' and (
                host.text == cfg['sshport'] and benv.text == '22' or
                host.text == cfg['soapport'] and benv.text == '7588'):
            forward.getparent().remove(forward)

def preprocess_proxy_add(xml, opt_proxy=None):
    """Add proxy to mirrors from CLI arguments or environment variable"""

    # Add proxy from CLI or env?
    set_proxy = opt_proxy or os.getenv("http_proxy")

    if set_proxy is None:
        return

    proxy_tag = "primary_proxy"

    # For all mirrors
    for mirror in xml.iterfind(".//mirror"):

        current_proxy = mirror.find(proxy_tag)

        # If there's already a proxy and we're trying to override it
        if current_proxy is not None:
            print('[WARN] Trying to override proxy "%s"!' %
                  current_proxy.text)
            continue

        # Add proxy to mirror
        proxy_e      = Element(proxy_tag)
        proxy_e.text = set_proxy

        mirror.append(proxy_e)

def preprocess_mirror_replacement(xml):
    """Do search and replace on mirror urls
       The sed patterns are a space separate list
       in cfg['mirrorsed']
    """

    ms = cfg['mirrorsed'].split()
    if (len(ms) % 2) == 1:
        raise XMLPreprocessError("Uneven number of (search, replace) Values !")

    # now zip even and uneven elements of mirrorsed.split()
    replacements = list(zip(islice(ms, 0, None, 2), islice(ms, 1, None, 2)))

    # do the replace in the text nodes
    victims = ['.//mirror/url-list/url/binary',
               './/mirror/url-list/url/source',
               './/mirror/url-list/url/key',
               './/mirror/primary_host']

    for v in victims:
        for u in xml.iterfind(v):
            for r in replacements:
                u.text = u.text.replace(r[0], r[1])

    # mirrorsite is special, because the url to be replaced is
    # in the 'value' attrib
    for u in xml.iterfind('//initvm/preseed/conf[@key="pbuilder/mirrorsite"]'):
        for r in replacements:
            u.attrib['value'] = u.attrib['value'].replace(r[0], r[1])

def preprocess_mirrors(xml):
    """Insert a trusted=yes mirror option for all mirrors if <noauth> is
    present.  Also convert binary option <binary> [opts] url </binary>
    to <option> tags.

    """

    # global noauth
    for node in xml.iterfind(".//noauth"):
        print("[WARN] <noauth> is deprecated. "
              "Use <option>trusted=yes</option> instead.")

        parent = node.getparent()

        # Add trusted=yes to primary mirror
        poptions = parent.find(".//mirror/options")
        if poptions is None:
            poptions = etree.Element("options")
            parent.find(".//mirror").append(poptions)

        ptrusted = etree.Element("option")
        ptrusted.text = "trusted=yes"
        poptions.append(ptrusted)

        # Add trusted=yes to all secondary mirrors
        for url in parent.iterfind(".//mirror/url-list/url"):
            options = url.find("options")
            if options is None:
                options = etree.Element("options")
                url.append(options)

            trusted = etree.Element("option")
            trusted.text = "trusted=yes"
            options.append(trusted)

        # TODO:old - Uncomment the following whenever there's no more
        # prj.has("noauth") in Elbe.  When this is done, also remove
        # noauth from dbsfed.xsd
        #
        # parent.remove(node)

    preg = re.compile(r".*\[(.*)\](.*)", re.DOTALL)

    # binary's and source's options
    for path in (".//mirror/url-list/url/binary",
                 ".//mirror/url-list/url/source"):

        for node in xml.iterfind(path):

            # e.g: <binary> [arch=amd64] http://LOCALMACHINE/something </binary>
            m = preg.match(node.text)

            if not m:
                continue

            # arch=amd64
            opt = m.group(1)

            # http://LOCALMACHINE/something
            node.text = m.group(2)

            # No <options>? Create it
            parent  = node.getparent()
            options = parent.find("options")
            if options is None:
                options = etree.Element("options")
                parent.append(options)

            # Adding subelement <option>
            option      = etree.Element("option")
            option.text = opt
            options.append(option)

def xmlpreprocess(fname, output, variants=None, proxy=None):

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

        preprocess_mirror_replacement(xml)

        preprocess_proxy_add(xml, proxy)

        # Change public PGP url key to raw key
        preprocess_pgp_key(xml)

        preprocess_iso_option(xml)

        preprocess_initvm_ports(xml)

        preprocess_mirrors(xml)

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


# TODO:py3 Remove object inheritance
# pylint: disable=useless-object-inheritance
class PreprocessWrapper(object):
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
        # pylint: disable=import-outside-toplevel
        # pylint: disable=cyclic-import
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
