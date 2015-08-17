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


import elbepack
from elbepack.treeutils import etree
from elbepack.validate import validate_xml
from elbepack.pkgutils import copy_kinitrd, NoKinitrdException
from elbepack.xmldefaults import ElbeDefaults
from elbepack.version import elbe_version
from elbepack.templates import write_template, get_initvm_preseed
from elbepack.directories import init_template_dir

from optparse import OptionParser

def run_command( argv ):
    oparser = OptionParser( usage="usage: %prog init [options] <filename>" )

    oparser.add_option( "--skip-validation", action="store_true",
                        dest="skip_validation", default=False,
                        help="Skip xml schema validation" )

    oparser.add_option( "--directory", dest="directory",
                        help="Working directory (default is build)",
                        metavar="FILE" )

    oparser.add_option( "--cdrom", dest="cdrom",
                        help="Use FILE as cdrom iso, and use that to build the initvm",
                        metavar="FILE" )

    oparser.add_option( "--proxy", dest="proxy",
                        help="Override the http Proxy" )

    oparser.add_option( "--buildtype", dest="buildtype",
                        help="Override the buildtype" )

    oparser.add_option( "--debug", dest="debug",
                        action="store_true", default=False,
           help="start qemu in graphical mode to enable console switch" )

    oparser.add_option( "--devel", dest="devel",
                        action="store_true", default=False,
           help="use devel mode, and install current builddir inside initvm" )

    (opt,args) = oparser.parse_args(argv)

    print opt.directory

    if len(args) == 0:
        print "no filename specified"
        oparser.print_help()
        sys.exit(20)
    elif len(args) > 1:
        print "too many filenames specified"
        oparser.print_help()
        sys.exit(20)

    if opt.devel:
        if not os.path.isdir("./elbepack" ):
            print "Devel Mode only valid, when running from elbe checkout"
            sys.exit(20)

    if not opt.skip_validation:
        validation = validate_xml (args[0])
        if len (validation) != 0:
            print "xml validation failed. Bailing out"
            for i in validation:
                print i
            sys.exit(20)

    xml = etree( args[0] )

    if not xml.has( "initvm" ):
        print "fatal error: xml missing mandatory section 'initvm'"
        sys.exit(20)

    if opt.buildtype:
        buildtype = opt.buildtype
    elif xml.has( "initvm/buildtype" ):
        buildtype = xml.text( "/initvm/buildtype" )
    else:
        buildtype = "nodefaults"

    defs = ElbeDefaults( buildtype )

    http_proxy = ""
    if os.getenv ("http_proxy"):
        http_proxy = os.getenv ("http_proxy")
    elif opt.proxy:
        http_proxy = opt.proxy
    elif xml.has("initvm/mirror/primary_proxy"):
        http_proxy = xml.text("initvm/mirror/primary_proxy")

    if opt.cdrom:
        mirror = xml.node ("initvm/mirror")
        mirror.clear ()
        cdrom = mirror.ensure_child ("cdrom")
        cdrom.set_text (os.path.abspath (opt.cdrom))

    if not opt.directory:
        path = "./build"
    else:
        path = opt.directory

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
         "prj": xml.node("/initvm"),
         "http_proxy": http_proxy,
         "pkgs": xml.node("/initvm/pkg-list") or [],
         "preseed": get_initvm_preseed(xml) }

    if http_proxy != "":
        os.putenv ("http_proxy", http_proxy)
        os.putenv ("https_proxy", http_proxy)
        os.putenv ("no_proxy", "localhost,127.0.0.1")

    try:
        copy_kinitrd(xml.node("/initvm"), out_path, defs, arch="amd64")
    except NoKinitrdException:
        print "Failure to download kernel/initrd debian Package"
        print "Check Mirror configuration"
        sys.exit(20)

    templates = os.listdir( init_template_dir )

    make_executable = [ "init-elbe.sh.mako",
                        "preseed.cfg.mako" ]

    for t in templates:
        o = t.replace( ".mako", "" )

        if t == "Makefile.mako":
            write_template(os.path.join(path,o), os.path.join(init_template_dir, t), d )
        else:
            write_template(os.path.join(out_path,o), os.path.join(init_template_dir, t), d )

        if t in make_executable:
            os.chmod( os.path.join(out_path,o), 0755 )

    shutil.copyfile( args[0],
       os.path.join(out_path, "source.xml" ) )

    if opt.devel:
        os.system( 'tar cvfj "%s" .' % os.path.join( out_path, "elbe-devel.tar.bz2" ) )
