# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2015, 2017 Linutronix GmbH

import __main__
import os
from pkgutil import iter_modules

import elbepack


# set global variables that are used in other modules via imports
elbe_exe = os.path.abspath(os.path.realpath(__main__.__file__))
elbe_dir = os.path.dirname(elbe_exe)

    if not elbe_exe.startswith('/usr/bin/'):

        # Set XML catalog if elbe is run from source
        xmlcat = os.path.join(elbe_dir, 'schema/catalog.xml')
        if os.environ.get('XML_CATALOG_FILES') is None:
            os.environ['XML_CATALOG_FILES'] = xmlcat
        else:
            os.environ['XML_CATALOG_FILES'] += ' '
            os.environ['XML_CATALOG_FILES'] += xmlcat


def get_cmdlist():
    return [x for _, x, _ in iter_modules(elbepack.commands.__path__)]


pack_dir = elbepack.__path__[0]

init_template_dir = os.path.join(pack_dir, 'init')
mako_template_dir = os.path.join(pack_dir, 'makofiles')

default_preseed_fname = os.path.join(pack_dir, 'default-preseed.xml')
xsdtoasciidoc_mako_fname = os.path.join(pack_dir, 'xsdtoasciidoc.mako')
