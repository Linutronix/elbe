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

from elbepack.elbexml import ElbeXML
from elbepack.rfs import BuildEnv
from elbepack.rpcaptcache import get_rpcaptcache
from elbepack.filesystem import TargetFs
from elbepack.filesystem import extract_target
from elbepack.dump import elbe_report, dump_fullpkgs, check_full_pkgs

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


def seed_files( outf, directory, slist, xml, xml_fname, opt, defs ):
    policy = os.path.join( directory, "usr/sbin/policy-rc.d" )
    write_file(policy, 0755, "#!/bin/sh\nexit 101\n")

    sources = os.path.join( directory, "etc/apt/sources.list" )
    write_file(sources, 0644, slist)

    d = {"elbe_version": elbe_version,
         "xml": xml,
         "prj": xml.node("/project"),
         "tgt": xml.node("/target"),
         "pkgs": xml.node("/target/pkg-list"),
         "fine": xml.node("/finetuning"),
         "preseed": get_preseed(xml),
         "defs": defs,
         "buildchroot": True,
         "opt": opt }

    prefs_fname = os.path.join( directory, "etc/apt/preferences" )
    write_template( prefs_fname, "preferences.mako", d )

    optelbe_fname = os.path.join( directory, "opt/elbe/" )
    outf.do( "mkdir -vp "+optelbe_fname )

    create_fname = os.path.join( directory, "opt/elbe/custom-preseed.cfg" )
    write_template( create_fname, "custom-preseed.cfg.mako", d )

    create_fname = os.path.join( directory, "opt/elbe/pkg-list" )
    write_template( create_fname, "pkg-list.mako", d )

    dump_fname = os.path.join( directory, "opt/elbe/source.xml" )
    os.system( 'cp "%s" "%s"' % (xml_fname, dump_fname) )

    create_fname = os.path.join( directory, "opt/elbe/part-target.sh" )
    write_template( create_fname, "part-target.sh.mako", d )
    os.chmod( create_fname, 0755 )

    create_fname = os.path.join( directory, "opt/elbe/finetuning.sh" )
    write_template( create_fname, "finetuning.sh.mako", d )
    os.chmod( create_fname, 0755 )

    create_fname = os.path.join( directory, "opt/elbe/mkcdrom.sh" )
    write_template( create_fname, "mkcdrom.sh.mako", d )
    os.chmod( create_fname, 0755 )


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

    chroot = os.path.join(opt.target, "chroot")
    os.system( 'mkdir -p "%s"' % chroot )

    outf = ASCIIDocLog(opt.output)

    if opt.name:
        outf.h1( "ELBE Report for Project "+opt.name )
    else:
        outf.h1( "ELBE Report" )

    outf.printo( "report timestamp: "+datetime.datetime.now().strftime("%Y%m%d-%H%M%S") )

    buildenv = BuildEnv(xml, outf, chroot)


    # XXX: need to add cdrom feature into buildenv
    #if prj.has("mirror/cdrom"):
    #    outf.do( 'mount -o loop "%s" "%s"' % (prj.text("mirror/cdrom"), os.path.join(chroot, "mnt")) )
    with buildenv:
        cache = get_rpcaptcache( buildenv.rfs, "aptcache.log", xml.text("project/arch", key="arch" ) )

        # XXX: cache update currently fails because of GPG Key... and some file issue.
        #cache.update()

        be_pkgs = buildenv.xml.get_buildenv_packages()
        ta_pkgs = buildenv.xml.get_target_packages()

        for p in be_pkgs + ta_pkgs:
            try:
                cache.mark_install( p, None )
            except KeyError:
                print "No Package " + p

        cache.commit()

    buildenv.seed_etc()

    #outf.chroot( chroot, "elbe create-target-rfs -t /target --buildchroot /opt/elbe/source.xml" )

    target = os.path.join(opt.target, "target")
    targetfs = TargetFs(target)

    os.chdir(buildenv.rfs.fname(''))

    extract_target( buildenv.rfs, xml, targetfs )
    targetfs.dump_elbeversion(xml)

    validation = os.path.join(opt.target, 'validation.txt')
    pkgs = xml.xml.node("/target/pkg-list")
    if xml.has("fullpkgs"):
        check_full_pkgs(pkgs, xml.xml.node("/fullpkgs"), validation, cache)
    else:
        check_full_pkgs(pkgs, None, validation, cache)

    dump_fullpkgs(xml, buildenv.rfs, cache)

    sourcexml = os.path.join(opt.target, 'source.xml')
    xml.xml.write(sourcexml)

    report = os.path.join(opt.target, "elbe-report.txt")
    elbe_report( xml, buildenv.rfs, cache, report )

    f = open(os.path.join(opt.target,"licence.txt"), "w+")
    buildenv.rfs.write_licenses(f)
    f.close()

    if cache.is_installed('grub-pc'):
        skip_grub = False
    else:
        print "package grub-pc is not installed, skipping grub"
        skip_grub = True

    targetfs.part_target(outf, xml, opt.target, skip_grub)

    #if not opt.skip_cdrom:
    #    outf.chroot( chroot, "/opt/elbe/mkcdrom.sh" )

