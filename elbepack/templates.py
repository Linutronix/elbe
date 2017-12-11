# ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (C) 2013  Linutronix GmbH
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

from __future__ import print_function

import os

from elbepack.treeutils import etree
from elbepack.directories import mako_template_dir, default_preseed_fname

from mako.template import Template
from mako import exceptions

def fix_linebreak_escapes (s):
    return s.replace('\\\n', '${"\\\\"}\n')

def template(fname, d, linebreak=False):
    try:
        if linebreak:
            return Template(filename=fname,preprocessor=fix_linebreak_escapes).render(**d)
        else:
            return Template(filename=fname).render(**d)
    except:
        print(exceptions.text_error_template().render())
        raise

def write_template( outname, fname, d, linebreak=False ):
    outfile = open(outname, "w")
    outfile.write( template( fname, d, linebreak ) )
    outfile.close()

def write_pack_template( outname, fname, d, linebreak=False ):
    template_name = os.path.join( mako_template_dir, fname )

    write_template( outname, template_name, d, linebreak )


def get_preseed( xml ):
    def_xml = etree( default_preseed_fname )

    preseed = {}
    for c in def_xml.node("/preseed"):
        k = (c.et.attrib["owner"], c.et.attrib["key"])
        v = (c.et.attrib["type"], c.et.attrib["value"])

        preseed[k] = v

    if not xml.has("./project/preseed"):
        return preseed

    for c in xml.node("/project/preseed"):
        k = (c.et.attrib["owner"], c.et.attrib["key"])
        v = (c.et.attrib["type"], c.et.attrib["value"])

        preseed[k] = v

    return preseed

def get_initvm_preseed( xml ):
    def_xml = etree( default_preseed_fname )

    preseed = {}
    for c in def_xml.node("/preseed"):
        k = (c.et.attrib["owner"], c.et.attrib["key"])
        v = (c.et.attrib["type"], c.et.attrib["value"])

        preseed[k] = v

    if not xml.has("./initvm/preseed"):
        return preseed

    for c in xml.node("/initvm/preseed"):
        k = (c.et.attrib["owner"], c.et.attrib["key"])
        v = (c.et.attrib["type"], c.et.attrib["value"])

        preseed[k] = v

    return preseed

def preseed_to_text( pres ):
    retval = ""
    for k,v in pres.items():
        retval += "%s\t%s\t%s\t%s\n" % (k[0], k[1], v[0], v[1])

    return retval

