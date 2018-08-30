# ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (c) 2015 Torben Hohn <torbenh@linutronix.de>
# Copyright (c) 2017 Philipp Arras <philipp.arras@linutronix.de>
# Copyright (c) 2017 Manuel Traut <manut@linutronix.de>
#
# SPDX-License-Identifier: GPL-3.0-or-later

import os

from pkgutil import iter_modules

import elbepack

elbe_exe = None
elbe_dir = None
examples_dir = None


def init_directories(elbe_relpath):
    # set global variables that are used in other modules via imports
    # this is the very first function that is called by 'elbe'
    global elbe_exe      #pylint: disable=global-statement
    global elbe_dir      #pylint: disable=global-statement
    global examples_dir  #pylint: disable=global-statement

    elbe_exe = os.path.abspath(elbe_relpath)
    elbe_dir = os.path.dirname(elbe_exe)

    if elbe_exe.startswith("/usr/bin/"):
        examples_dir = "/usr/share/doc/elbe-doc/examples"
    else:
        examples_dir = os.path.join(elbe_dir, "examples")

        # Set XML catalog if elbe is run from source
        xmlcat = os.path.join(elbe_dir, "schema/catalog.xml")
        if os.environ.get('XML_CATALOG_FILES') is None:
            os.environ['XML_CATALOG_FILES'] = xmlcat
        else:
            os.environ['XML_CATALOG_FILES'] += " "
            os.environ['XML_CATALOG_FILES'] += xmlcat


def get_cmdlist():
    return [x for _, x, _ in iter_modules(elbepack.commands.__path__)]


pack_dir = elbepack.__path__[0]

init_template_dir = os.path.join(pack_dir, "init")
mako_template_dir = os.path.join(pack_dir, "makofiles")

default_preseed_fname = os.path.join(pack_dir, "default-preseed.xml")
xsdtoasciidoc_mako_fname = os.path.join(pack_dir, "xsdtoasciidoc.mako")
