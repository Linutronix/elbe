# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2017-2018 Linutronix GmbH

import contextlib
import logging
import os
import pathlib
import re
import sys
import tempfile
import warnings
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

from lxml import etree
from lxml.etree import Element, SubElement, XMLParser

with warnings.catch_warnings():
    # passlib has code to handle absence of the crypt module and will work just
    # fine for our usecase without it.
    warnings.filterwarnings('ignore', "'crypt' is deprecated", DeprecationWarning)
    from passlib.hash import sha512_crypt

from elbepack.archivedir import ArchivedirError, combinearchivedir
from elbepack.config import cfg
from elbepack.isooptions import iso_option_valid
from elbepack.treeutils import dbsfed_schema, xml_bool
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
        print(f'[WARN] <key>{key.text}</key> is deprecated. '
              'You should use raw-key instead.')
        try:
            keyurl = key.text.strip().replace('LOCALMACHINE', 'localhost')
            myKey = urlopen(keyurl).read().decode('ascii')
            key.tag = 'raw-key'
            key.text = f'\n{myKey}\n'
        except HTTPError:
            raise XMLPreprocessError(
                f'Invalid PGP Key URL in <key> tag: {keyurl}')
        except URLError:
            raise XMLPreprocessError(
                f'Problem with PGP Key URL in <key> tag: {keyurl}')


def preprocess_bootstrap(xml):
    """Replaces a maybe existing debootstrapvariant element with debootstrap"""

    old_node = xml.find('.//debootstrapvariant')
    if old_node is None:
        return

    print('[WARN] <debootstrapvariant> is deprecated. Use <debootstrap> instead.')

    bootstrap = Element('debootstrap')

    bootstrap_variant = Element('variant')
    bootstrap_variant.text = old_node.text
    bootstrap.append(bootstrap_variant)

    old_includepkgs = old_node.get('includepkgs')
    if old_includepkgs:
        bootstrap_include = Element('include')
        bootstrap_include.text = old_includepkgs
        bootstrap.append(bootstrap_include)

    old_node.getparent().replace(old_node, bootstrap)


def preprocess_tune2fs(xml):
    """Replaces all maybe existing tune2fs elements with fs-finetuning command"""

    old_nodes = xml.findall('.//tune2fs')
    for old_node in old_nodes:
        print('[WARN] <tune2fs> is deprecated. Use <fs-finetuning> instead.')

        fs_node = old_node.getparent()
        finetuning_node = fs_node.find('fs-finetuning')
        if finetuning_node is None:
            finetuning_node = SubElement(fs_node, 'fs-finetuning')

        command = SubElement(finetuning_node, 'device-command')
        command.text = f'tune2fs {old_node.text} {{device}}'

        fs_node.remove(old_node)


def preprocess_iso_option(xml):

    src_opts = xml.find('.//src-cdrom/src-opts')
    if src_opts is None:
        return

    strict = xml_bool(src_opts.attrib.get('strict'))

    for opt in src_opts.iterfind('./*'):
        valid = iso_option_valid(opt.tag, opt.text)
        if valid is True:
            continue

        tag = f'<{opt.tag}>{opt.text}</{opt.tag}>'

        if valid is False:
            violation = f'Invalid ISO option {tag}'
        elif isinstance(valid, int):
            violation = (
                f'Option {tag} will be truncated by {valid} characters')
        elif isinstance(valid, str):
            violation = (
                f"Character '{valid}' ({ord(valid[0])}) in ISO option {tag} "
                'violated ISO-9660')
        if strict:
            raise XMLPreprocessError(violation)
        print(f'[WARN] {violation}')


def preprocess_initvm_ports(xml, sshport):
    """Filters out the default port forwardings to prevent qemu conflict"""

    for forward in xml.iterfind('initvm/portforwarding/forward'):
        prot = forward.find('proto')
        benv = forward.find('buildenv')
        host = forward.find('host')
        if prot is None or benv is None or host is None:
            continue
        if prot.text == 'tcp' and (
                host.text == sshport and benv.text == '22' or
                host.text == cfg['soapport'] and benv.text == '7588'):
            forward.getparent().remove(forward)


def preprocess_pkg_pinning(xml):
    """Do search and replace on pkg attributes, replacing 'pin' with 'release-name'."""

    errors = False
    for pkg in xml.iterfind('.//target/pkg-list/pkg'):
        if 'pin' in pkg.attrib:
            if 'release-name' in pkg.attrib:
                logging.error(
                    'Found attributes "pin" and "release-name" for "%s". '
                    'Please remove attribute "pin".',
                    pkg.text)
                errors = True
                continue

            logging.warning(
                'Attribute pin= for element <pkg> is deprecated. Use release-name= instead.')

            pkg.attrib['release-name'] = pkg.attrib['pin']
            del pkg.attrib['pin']

        # Check that max one attribute of 'version', 'origin', 'release-*' is set
        if ('version' in pkg.attrib) \
            + ('origin' in pkg.attrib) \
            + (0 != len([a for a in pkg.attrib if a.startswith('release-')])) \
                > 1:
            logging.error(
                'Invalid pkg pinning attribute combination for "%s".'
                ' Use only either of "version" OR "origin" OR "release-* | pin"',
                pkg.text)
            errors = True

    if errors:
        raise XMLPreprocessError('Invalid package pinning attributes')


def preprocess_check_script(xml, basedir):
    """Inline check scripts"""

    for script in xml.iterfind('.//check-image-list/check-script'):
        location = script.attrib.pop('location', None)
        if location is None:
            continue

        script.text = basedir.joinpath(location).read_text()


def preprocess_proxy_add(xml, opt_proxy=None):
    """Add proxy to mirrors from CLI arguments or environment variable"""

    # Add proxy from CLI or env?
    set_proxy = opt_proxy or os.getenv('http_proxy')

    if set_proxy is None:
        return

    proxy_tag = 'primary_proxy'

    # For all mirrors
    for mirror in xml.iterfind('.//mirror'):

        current_proxy = mirror.find(proxy_tag)

        # If there's already a proxy and we're trying to override it
        if current_proxy is not None:
            print(f'[WARN] Trying to override proxy "{current_proxy.text}"!')
            continue

        # Add proxy to mirror
        proxy_e = Element(proxy_tag)
        proxy_e.text = set_proxy

        mirror.append(proxy_e)


def preprocess_mirrors(xml):
    """Insert a trusted=yes mirror option for all mirrors if <noauth> is
    present.  Also convert binary option <binary> [opts] url </binary>
    to <option> tags.

    """

    # global noauth
    for node in xml.iterfind('.//noauth'):
        print('[WARN] <noauth> is deprecated. '
              'Use <option>trusted=yes</option> instead.')

        parent = node.getparent()

        # Add trusted=yes to primary mirror
        poptions = parent.find('.//mirror/options')
        if poptions is None:
            poptions = etree.Element('options')
            parent.find('.//mirror').append(poptions)

        ptrusted = etree.Element('option')
        ptrusted.text = 'trusted=yes'
        poptions.append(ptrusted)

        # Add trusted=yes to all secondary mirrors
        for url in parent.iterfind('.//mirror/url-list/url'):
            options = url.find('options')
            if options is None:
                options = etree.Element('options')
                url.append(options)

            trusted = etree.Element('option')
            trusted.text = 'trusted=yes'
            options.append(trusted)

        # TODO:old - Uncomment the following whenever there's no more
        # prj.has("noauth") in Elbe.  When this is done, also remove
        # noauth from dbsfed.xsd
        #
        # parent.remove(node)

    preg = re.compile(r'.*\[(.*)\](.*)', re.DOTALL)

    # binary's and source's options
    for path in ('.//mirror/url-list/url/binary',
                 './/mirror/url-list/url/source'):

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
            parent = node.getparent()
            options = parent.find('options')
            if options is None:
                options = etree.Element('options')
                parent.append(options)

            # Adding subelement <option>
            option = etree.Element('option')
            option.text = opt
            options.append(option)


def _hash_password(passwd):
    return sha512_crypt.using(rounds=5000).hash(passwd)


def preprocess_passwd(xml):
    """Preprocess plain-text passwords. Plain-text passwords for root and
       adduser will be replaced with their hashed values.
    """

    # migrate root password
    for passwd in xml.iterfind('.//target/passwd'):
        # legacy support: move plain-text password to login action
        if xml.find('.//action/login') is not None:
            xml.find('.//action/login').text = passwd.text

        passwd.tag = 'passwd_hashed'
        passwd.text = _hash_password(passwd.text)
        logging.warning('Please replace <passwd> with <passwd_hashed>. '
                        'The generated sha512crypt hash only applies 5000 rounds for '
                        'backwards compatibility reasons. This is considered insecure nowadays.')

    # migrate user passwords
    for adduser in xml.iterfind('.//target/finetuning/adduser[@passwd]'):
        passwd = adduser.attrib['passwd']
        adduser.attrib['passwd_hashed'] = _hash_password(passwd)
        del adduser.attrib['passwd']
        logging.warning("Please replace adduser's passwd attribute with passwd_hashed. "
                        'The generated sha512crypt hash only applies 5000 rounds for '
                        'backwards compatibility reasons. This is considered insecure nowadays.')


def xmlpreprocess(xml_input_file, xml_output_file, *, sshport, variants=None, proxy=None, gzip=9):
    """Preprocesses the input XML data to make sure the `output`
       can be validated against the current schema.
       `xml_input_file` is a path (str) to the input file.
       `xml_output_file` is a path (str) to the output file.
    """

    # first convert variants to a set
    if not variants:
        variants = set([])
    else:
        variants = set(variants)

    parser = XMLParser(huge_tree=True)
    schema = dbsfed_schema()

    try:
        xml = etree.parse(xml_input_file, parser=parser)
        xml.xinclude()

        basedir = pathlib.Path(xml_input_file).parent

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

        preprocess_proxy_add(xml, proxy)

        # Change public PGP url key to raw key
        preprocess_pgp_key(xml)

        # Replace old debootstrapvariant with debootstrap
        preprocess_bootstrap(xml)

        # Replace old tune2fs with fs-finetuning command
        preprocess_tune2fs(xml)

        preprocess_iso_option(xml)

        preprocess_initvm_ports(xml, sshport)

        preprocess_mirrors(xml)

        preprocess_passwd(xml)

        preprocess_pkg_pinning(xml)

        preprocess_check_script(xml, basedir)

        if schema.validate(xml):
            # if validation succedes write xml file
            xml.write(
                xml_output_file,
                encoding='UTF-8',
                pretty_print=True,
                compression=gzip)
            # the rest of the code is exception and error handling
            return

    except etree.XMLSyntaxError:
        raise XMLPreprocessError('XML Parse error\n' + str(sys.exc_info()[1]))
    except ArchivedirError:
        raise XMLPreprocessError('<archivedir> handling failed\n' +
                                 str(sys.exc_info()[1]))
    except BaseException:
        raise XMLPreprocessError(
            'Unknown Exception during validation\n' + str(sys.exc_info()[1]))

    # We have errors, return them in string form...
    raise XMLPreprocessError('\n'.join(error_log_to_strings(schema.error_log)))


@contextlib.contextmanager
def preprocess_file(xmlfile, *, variants, sshport):
    with tempfile.NamedTemporaryFile(suffix='elbe.xml') as preproc:
        xmlpreprocess(xmlfile, preproc, variants=variants, sshport=sshport)
        preproc.seek(0)
        yield preproc.name
