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

def unbase( s, fname ):
    outfile = file(fname, "w")
    outfile.write( standard_b64decode(s) )
    outfile.close()

def enbase( fname ):
    infile = file(fname, "r")
    s = infile.read()
    return standard_b64encode(s)

def get_preseed( xml ):
    pack_dir = elbepack.__path__[0]
    def_xml = etree( os.path.join( pack_dir, "default-preseed.xml" ) )

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

def run_command( argv ):
    pack_dir = elbepack.__path__[0]
    template_dir = os.path.join( pack_dir, "mako" )

    oparser = OptionParser( usage="usage: %prog create [options] <filename>" )

    oparser.add_option( "--oldkvm", action="store_true", dest="oldkvm",
                        default=False,
                        help="We are building for an old kvm version" )

    oparser.add_option( "--debug", action="store_true", dest="debug",
                        default=False,
                        help="Enable various features to debug the build" )

    oparser.add_option( "--skip-validation", action="store_true",
                        dest="skip_validation", default=False,
                        help="Skip xml schema validation" )

    oparser.add_option( "--skip-cds", action="store_true", dest="skip_cds",
                        default=False,
                        help="Skip cd generation" )

    oparser.add_option( "--directory", dest="dir",
                        help="Write Makefile into specified directory",
                        metavar="FILE" )

    oparser.add_option( "--buildtype", dest="buildtype",
                        help="Override the buildtype" )

    oparser.add_option( "--build-source", action="store_true",
                        dest="buildsources", default=False,
                        help="Build source cdrom" )

    oparser.add_option( "--proxy", dest="proxy",
                        help="Override the http Proxy" )

    (opt,args) = oparser.parse_args(argv)

    if len(args) == 0:
        print "No Filename specified"
        oparser.print_help()
        sys.exit(20)

    if len(args) > 1:
        print "too many filenames specified"
        oparser.print_help()
        sys.exit(20)

    try:
        if not opt.skip_validation:
            if not validate_xml( args[0] ):
                print "xml validation failed. Bailing out"
                sys.exit(20)

        xml = etree( args[0] )
    except:
        print "Unable to open xml File. Bailing out"
        sys.exit(20)

    if opt.buildtype:
        buildtype = opt.buildtype
    elif xml.has( "project/buildtype" ):
        buildtype = xml.text( "/project/buildtype" )
    else:
        buildtype = "nodefaults"

    if opt.proxy:
        http_proxy = opt.proxy
    elif xml.has("project/mirror/primary_proxy"):
        http_proxy = xml.text("project/mirror/primary_proxy")
    else:
        http_proxy = ""

    defs = ElbeDefaults( buildtype )

    if xml.node("/project/mirror/url-list"):
        for n in xml.node("/project/mirror/url-list"):
           if n.has("binary"):
             if n.text("binary").find("localhost") != -1:
               print "localhost is not allowed as url - use LOCALMACHINE to refer to your system."
               sys.exit(40)
           if n.has("source"):
             if n.text("source").find("localhost") != -1:
               print "localhost is not allowed as url - use LOCALMACHINE to refer to your system."
               sys.exit(40)

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
         "opt": opt,
         "xml": xml,
         "prj": xml.node("/project"),
         "tgt": xml.node("/target"),
         "pkgs": xml.node("/target/pkg-list"),
         "fine": xml.node("/finetuning"),
         "defs": defs,
         "http_proxy": http_proxy,
         "buildchroot": False,
         "preseed": get_preseed(xml) }

    try:
        copy_kinitrd(xml, out_path, defs)
    except:
        print "Failure to download kernel/initrd debian Package"
        print "Check your source URLs"
        sys.exit(20)

    if xml.has("archive"):
        unbase( xml.text("/archive"), os.path.join(out_path,"archive.tar.bz2") )

    templates = os.listdir( template_dir )

    make_executable = [ "02pinning.mako",
                        "finetuning.sh.mako",
                        "changeroot-into-buildenv.sh.mako",
                        "cp-scipts-into-buildenv.sh.mako",
                        "create-target-rfs.sh.mako",
                        "part-target.sh.mako",
                        "post-inst.sh.mako",
                        "print_licence.sh.mako",
                        "mkcdrom.sh.mako" ]

    for t in templates:
        print t
        o = t.replace( ".mako", "" )
        if t == "Makefile.mako":
            write_template(os.path.join(path,o), os.path.join(template_dir, t), d )
        else:
            write_template(os.path.join(out_path,o), os.path.join(template_dir, t), d )

        if t in make_executable:
            os.chmod( os.path.join(out_path,o), 0755 )

    shutil.copyfile( args[0],
       os.path.join(out_path, "source.xml" ) )
