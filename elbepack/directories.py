# ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (C) 2015  Linutronix GmbH
#
# This file is part of ELBE.
#
# ELBE is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# ELBE is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with ELBE.  If not, see <http://www.gnu.org/licenses/>.

import elbepack
import os
from pkgutil import iter_modules

elbe_exe = None
elbe_dir = None
examples_dir = None


def init_directories(elbe_relpath):
    global elbe_exe
    global elbe_dir
    global examples_dir

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
elbe_pubkey_fname = os.path.join(pack_dir, "elbe-repo.pub")
