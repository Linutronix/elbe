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

from optparse import OptionParser
import datetime
import sys
import os

from mako.template import Template
from mako import exceptions

import elbepack
from elbepack.treeutils import etree
from elbepack.version import elbe_version
from elbepack.asciidoclog import ASCIIDocLog

from elbepack.elbexml import ElbeXML, ValidationError
from elbepack.rfs import BuildEnv
from elbepack.rpcaptcache import get_rpcaptcache
from elbepack.filesystem import TargetFs
from elbepack.filesystem import extract_target
from elbepack.dump import elbe_report, dump_fullpkgs, check_full_pkgs, dump_debootstrappkgs

from elbepack.cdroms import mk_source_cdrom, mk_binary_cdrom


def read_file( fname ):
    f = file( fname, "r" )
    d = f.read()
    f.close()
    return d

def write_file( fname, mode, cont ):
    f = file( fname, "w" )
    f.write(cont)
    f.close()
    os.chmod( fname, mode )



# Some more helpers
def template(fname, d):
    try:
        return Template(filename=fname).render(**d)
    except:
        print exceptions.text_error_template().render()
        raise

def write_template( outname, fname, d ):
    pack_dir = elbepack.__path__[0]
    template_dir = os.path.join( pack_dir, "mako" )

    outfile = file(outname, "w")
    outfile.write( template( os.path.join(template_dir, fname), d ) )
    outfile.close()

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
    oparser = OptionParser(usage="usage: %prog buildchroot [options] <xmlfile>")
    oparser.add_option( "-t", "--target", dest="target",
                        help="directoryname of target" )
    oparser.add_option( "-o", "--output", dest="output",
                        help="name of logfile" )
    oparser.add_option( "-n", "--name", dest="name",
                        help="name of the project (included in the report)" )
    oparser.add_option( "--skip-validation", action="store_true",
                        dest="skip_validation", default=False,
                        help="Skip xml schema validation" )
    oparser.add_option( "--skip-debootstrap", action="store_true",
                        dest="skip_debootstrap", default=False,
                        help="Skip debootstrap" )
    oparser.add_option( "--skip-cdrom", action="store_true",
                        dest="skip_cdrom", default=False,
                        help="Skip cdrom iso generation" )
    oparser.add_option( "--build-sources", action="store_true",
                        dest="buildsources", default=False,
                        help="Build Source CD" )
    oparser.add_option( "--debug", action="store_true", dest="debug",
                        default=False,
                        help="Enable various features to debug the build" )
    oparser.add_option( "--buildtype", dest="buildtype",
                        help="Override the buildtype" )
    oparser.add_option( "--proxy", dest="proxy",
                        help="Override the http proxy" )

    (opt,args) = oparser.parse_args(argv)

    if len(args) != 1:
        print "wrong number of arguments"
        oparser.print_help()
        sys.exit(20)

    if not opt.output:
        print "No Log output"
        sys.exit(20)
    if not opt.target:
        print "No target specified"
        sys.exit(20)

    opt.target = os.path.abspath(opt.target)

    if opt.buildtype:
        buildtype = opt.buildtype
    else:
        buildtype = None

    try:
        xml = ElbeXML( args[0], buildtype=buildtype, skip_validate=opt.skip_validation )
    except ValidationError:
        print "xml validation failed. Bailing out"
        sys.exit(20)

    outf = ASCIIDocLog(opt.output)

    if opt.name:
        outf.h1( "ELBE Report for Project "+opt.name )
    else:
        outf.h1( "ELBE Report" )

    outf.printo( "report timestamp: "+datetime.datetime.now().strftime("%Y%m%d-%H%M%S") )

    chroot = os.path.join(opt.target, "chroot")
    outf.do( 'mkdir -p "%s"' % chroot )

    buildenv = BuildEnv(xml, outf, chroot)

    with buildenv:
        cache = get_rpcaptcache( buildenv.rfs, "aptcache.log", xml.text("project/arch", key="arch" ) )

        # First Update the apt cache
        try:
            cache.update()
        except:
            outf.printo ("update cache failed")

        # Then dump the debootstrap Packages

        if buildenv.fresh_debootstrap:
            dump_debootstrappkgs(xml, cache)
            source = xml
        else:
            sourcepath = os.path.join(opt.target, "source.xml" )
            source = ElbeXML( sourcepath, buildtype=buildtype, skip_validate=opt.skip_validation )
            xml.get_debootstrappkgs_from( source )

        # Seed etc, we need /etc/hosts for hostname -f to work correctly
        buildenv.seed_etc()

        # Now install Packages from all sources

        be_pkgs = buildenv.xml.get_buildenv_packages()
        ta_pkgs = buildenv.xml.get_target_packages()

        for p in be_pkgs + ta_pkgs:
            try:
                cache.mark_install( p, None )
            except KeyError:
                outf.printo ("No Package " + p)
            except SystemError:
                outf.printo ("Unable to correct problems " + p)
        try:
            cache.commit()
        except SystemError:
            outf.printo ("commiting changes failed")


    # Now start with the extraction of the TargetFs

    target = os.path.join(opt.target, "target")
    targetfs = TargetFs(target, outf, buildenv.xml)

    os.chdir(buildenv.rfs.fname(''))

    extract_target( buildenv.rfs, xml, targetfs, outf, cache )


    # Package Validation and Package lists

    validation = os.path.join(opt.target, 'validation.txt')
    pkgs = xml.xml.node("/target/pkg-list")
    if xml.has("fullpkgs"):
        check_full_pkgs(pkgs, xml.xml.node("/fullpkgs"), validation, cache)
    else:
        check_full_pkgs(pkgs, None, validation, cache)

    dump_fullpkgs(xml, buildenv.rfs, cache)

    # Dump a few things

    try:
        targetfs.dump_elbeversion (xml)
    except MemoryError:
        outf.printo ("dump elbeversion failed")

    try:
        sourcexml = os.path.join(opt.target, 'source.xml')
        xml.xml.write(sourcexml)
    except MemoryError:
        outf.printo ("write source.xml failed (archive to huge?)")

    # Elbe Report

    report = os.path.join(opt.target, "elbe-report.txt")
    elbe_report( xml, buildenv.rfs, cache, report, targetfs )

    f = open(os.path.join(opt.target,"licence.txt"), "w+")
    buildenv.rfs.write_licenses(f, outf)
    f.close()


    # Generate images

    if cache.is_installed('grub-pc'):
        skip_grub = False
    else:
        print "package grub-pc is not installed, skipping grub"
        skip_grub = True

    targetfs.part_target(opt.target, skip_grub)

    # build cdrom images
    arch = xml.text("project/arch", key="arch" )
    codename = xml.text("project/suite")

    if not opt.skip_cdrom:
        mk_binary_cdrom( buildenv.rfs, arch, codename, xml, opt.target )
        if opt.buildsources:
            mk_source_cdrom( buildenv.rfs, arch, codename, opt.target )

    if targetfs.images:
        fte = open(os.path.join(opt.target,"files-to-extract"), "w+")
        # store each used image only once
        files = set(targetfs.images)
        print "generated files:"
        for img in files:
            fte.write(img + '\n')
        fte.write("source.xml\n")
        fte.write("licence.txt\n")
        fte.write("validation.txt\n")
        fte.write("elbe-report.txt\n")
        fte.write("../elbe-report.log\n")
        fte.close()

