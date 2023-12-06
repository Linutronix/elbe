# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2022 Linutronix GmbH

import functools
import os
import sys

from http.server import SimpleHTTPRequestHandler, HTTPServer
from threading import Thread

from lxml.etree import XMLParser, parse, Element, XMLSyntaxError


class RepodirError(Exception):
    pass


def preprocess_repodir(xml, xmldir):
    """Replaces each <repodir>, which points to a directory containing a Debian
       repository, with a valid <url> element.
       <repodir>'s text node holds a filepath plus the elements of a sources.list
       entry after the URL (suite, components).

       Returns a list with HTTPServer instances.
    """
    httpds = []
    for repodir in xml.iterfind('.//mirror/url-list/repodir'):
        repo = repodir.text.split(maxsplit=1)
        if len(repo) != 2:
            raise RepodirError("A <repodir> must consist of a file path,"
                               "a suite name, and components")

        hostdir = os.path.join(xmldir, repo[0])
        httpd = HTTPServer(('localhost', 0),
                           functools.partial(SimpleHTTPRequestHandler, directory=hostdir))

        url_element = Element("url")
        # Keep the variant attribute for later processing
        if 'variant' in repodir.attrib:
            url_element.attrib['variant'] = repodir.attrib['variant']

        bin_el = Element("binary")
        bin_el.text = f"http://LOCALMACHINE:{httpd.server_address[1]} {repo[1]}"
        url_element.append(bin_el)
        src_el = Element("source")
        src_el.text = bin_el.text
        url_element.append(src_el)

        if 'signed-by' in repodir.attrib:
            try:
                keyfile = os.path.join(hostdir, repodir.attrib['signed-by'])
                auth_el = Element("raw-key")
                auth_el.text = "\n" + open(keyfile, encoding='ascii').read()
            except Exception:
                raise RepodirError(
                    f"{keyfile} is not a valid ascii-armored OpenPGP keyring")
        else:
            auth_el = Element("options")
            option_el = Element("option")
            option_el.text = "trusted=yes"
            auth_el.append(option_el)
        url_element.append(auth_el)

        httpds.append(httpd)

        repodir.getparent().append(url_element)
        repodir.getparent().remove(repodir)

    return httpds


class Repodir:
    """Constructs a Repodir."""
    def __init__(self, input_xml_path, output_xml_path):
        self.input = input_xml_path
        self.output = output_xml_path
        self.httpds = []

    def __enter__(self):
        parser = XMLParser(huge_tree=True)

        try:
            xml = parse(self.input, parser=parser)
            xml.xinclude()

            self.httpds = preprocess_repodir(xml, os.path.dirname(self.input))

            xml.write(
                self.output,
                encoding="UTF-8",
                pretty_print=True)

            for httpd in self.httpds:
                Thread(target=httpd.serve_forever).start()

            return self

        except XMLSyntaxError:
            raise RepodirError(f"XML Parse error\n{sys.exc_info()[1]}")
        except BaseException:
            raise RepodirError(
                f"Unknown Exception during validation\n{str(sys.exc_info()[1])}")

    def __exit__(self, _typ, _value, _traceback):
        for httpd in self.httpds:
            httpd.shutdown()
