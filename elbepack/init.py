#!/usr/bin/env python
#
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

import os
import sys
import shutil

from mako.template import Template
from mako import exceptions
from base64 import standard_b64decode, standard_b64encode

import elbepack
from elbepack.treeutils import etree
from elbepack.validate import validate_xml
from elbepack.pkgutils import copy_kinitrd
from elbepack.xmldefaults import ElbeDefaults
from elbepack.version import elbe_version

from optparse import OptionParser

# Some more helpers
def template(fname, d):
    try:
        return Template(filename=fname).render(**d)
    except:
        print exceptions.text_error_template().render()
        raise

def write_template( outname, fname, d ):
    outfile = file(outname, "w")
    outfile.write( template( fname, d ) )
    outfile.close()

def run_command( argv ):
    pack_dir = elbepack.__path__[0]
    template_dir = os.path.join( pack_dir, "init" )

    oparser = OptionParser( usage="usage: %prog init [options] <filename>" )

    oparser.add_option( "--skip-validation", action="store_true",
                        dest="skip_validation", default=False,
                        help="Skip xml schema validation" )

    oparser.add_option( "--skip-cds", action="store_true", dest="skip_cds",
                        default=False,
                        help="Skip cd generation" )

    oparser.add_option( "--directory", dest="dir",
                        help="Working directory (default is build)",
                        metavar="FILE" )

    oparser.add_option( "--build-source", action="store_true",
                        dest="buildsources", default=False,
                        help="Build source cdrom" )

    oparser.add_option( "--proxy", dest="proxy",
                        help="Override the http Proxy" )

    oparser.add_option( "--buildtype", dest="buildtype",
                        help="Override the buildtype" )

    (opt,args) = oparser.parse_args(argv)

    if len(args) == 0:
        print "no filename specified"
        oparser.print_help()
        sys.exit(20)
    elif len(args) > 1:
        print "too many filenames specified"
        oparser.print_help()
        sys.exit(20)

    if not opt.skip_validation:
        if not validate_xml( args[0] ):
            print "xml validation failed. Bailing out"
            sys.exit(20)

    xml = etree( args[0] )

    if opt.buildtype:
        buildtype = opt.buildtype
    elif xml.has( "project/buildtype" ):
        buildtype = xml.text( "/project/buildtype" )
    else:
        buildtype = "nodefaults"

    defs = ElbeDefaults( buildtype )

    http_proxy = ""
    if opt.proxy:
        http_proxy = opt.proxy
    elif xml.has("project/mirror/primary_proxy"):
        http_proxy = xml.text("project/mirror/primary_proxy")

    if not opt.dir:
        path = "./build"
    else:
        path = opt.dir

    try:
        os.makedirs(path)
    except:
        print 'unable to create project directory: %s' % path
        sys.exit(30)

    out_path = os.path.join(path,".elbe-in")
    try:
        os.makedirs(out_path)
    except:
        print 'unable to create subdirectory: %s' % out_path
        sys.exit(30)

    d = {"elbe_version": elbe_version,
         "defs": defs,
         "opt": opt,
         "xml": xml,
         "prj": xml.node("/project"),
         "tgt": xml.node("/target"),
         "http_proxy": http_proxy }

    try:
        copy_kinitrd(xml, out_path, defs, arch="amd64")
    except:
        print "Failure to download kernel/initrd debian Package"
        print "Check Mirror configuration"
        sys.exit(20)

    templates = os.listdir( template_dir )

    make_executable = [ "init-elbe.sh.mako",
                        "preseed.cfg.mako" ]

    for t in templates:
        o = t.replace( ".mako", "" )

        if t == "Makefile.mako":
            write_template(os.path.join(path,o), os.path.join(template_dir, t), d )
        else:
            write_template(os.path.join(out_path,o), os.path.join(template_dir, t), d )

        if t in make_executable:
            os.chmod( os.path.join(out_path,o), 0755 )

    shutil.copyfile( args[0],
       os.path.join(out_path, "source.xml" ) )
