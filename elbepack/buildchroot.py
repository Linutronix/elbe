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

from treeutils import etree
from optparse import OptionParser
from subprocess import Popen, PIPE, STDOUT
import datetime
import apt
import sys
import os
import string

from mako.template import Template
from mako import exceptions

import elbepack
from elbepack.treeutils import etree
from elbepack.validate import validate_xml
from elbepack.xmldefaults import ElbeDefaults
from elbepack.version import elbe_version

class commanderror(Exception):
    def __init__(self, cmd, returncode):
        self.returncode = returncode
        self.cmd = cmd

    def __repr__(self):
        return "Error: %d returned from Command %s" % (self.returncode, self.cmd)

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

class asccidoclog(object):
    def __init__(self, fname):
        if os.path.isfile(fname):
            os.unlink(fname)
        self.fp = file(fname, "w")

    def printo(self, text=""):
        self.fp.write(text+"\n")

    def print_raw(self, text):
        self.fp.write(text)

    def h1(self, text):
        self.printo()
        self.printo(text)
        self.printo("="*len(text))
        self.printo()

    def h2(self, text):
        self.printo()
        self.printo(text)
        self.printo("-"*len(text))
        self.printo()

    def table(self):
        self.printo( "|=====================================" )

    def verbatim_start(self):
        self.printo( "------------------------------------------------------------------------------" )

    def verbatim_end(self):
        self.printo( "------------------------------------------------------------------------------" )
        self.printo()

    def do_command(self, cmd, **args):

        if args.has_key("allow_fail"):
            allow_fail = args["allow_fail"]
        else:
            allow_fail = False

	self.printo( "running cmd +%s+" % cmd )
	self.verbatim_start()
	p = Popen(cmd, shell=True, stdout=PIPE, stderr=STDOUT )
	output, stderr = p.communicate()
	self.print_raw( output )
	self.verbatim_end()


	if p.returncode != 0:
	    self.printo( "Command failed with errorcode %d" % p.returncode )
            if not allow_fail:
                raise commanderror(cmd, p.returncode)

    def get_command_out(self, cmd, **args):

        if args.has_key("allow_fail"):
            allow_fail = args["allow_fail"]
        else:
            allow_fail = False

	self.printo( "getting output from cmd +%s+" % cmd )
	self.verbatim_start()
	p = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE )
	output, stderr = p.communicate()
	self.print_raw( stderr )
	self.verbatim_end()


	if p.returncode != 0:
	    self.printo( "Command failed with errorcode %d" % p.returncode )
            if not allow_fail:
                raise commanderror(cmd, p.returncode)

        return output

def check_full_pkgs(pkgs, errorname):
    elog = asccidoclog(errorname)

    elog.h1("ELBE Package validation")

    errors = 0
    cache = apt.cache.Cache( memonly=True )
    pindex = {}
    for p in pkgs:
        name = p.et.text
        ver  = p.et.get('version')
        md5  = p.et.get('md5')

        pindex[name] = p

        cp = cache[name]

        if not cp:
            elog.printo( "- package %s not installed" % name )
            errors += 1

        if cp.installed.version != ver:
            elog.printo( "- package %s version %s does not match installed version %s" % (name, ver,  cp.installed.version) )
            errors += 1

        if cp.installed.md5 != md5:
            elog.printo( "- package %s md5 %s does not match installed md5 %s" % (name, md5,  cp.installed.md5) )
            errors += 1

    for cp in cache:
        if cp.is_installed:
            if not pindex.has_key(cp.name):
                elog.printo( "additional package %s installed, that was not requested" % cp.name )
                errors += 1

    if errors == 0:
        elog.printo( "No Errors found" )

def debootstrap( outf, directory, mirror, suite, target_arch, defs ):

    current_arch = outf.get_command_out( "dpkg --print-architecture" )
    current_arch = current_arch.strip()

    print current_arch, target_arch

    outf.h2( "debootstrap log" )

    if current_arch == target_arch:
        debootstrap_cmd = 'debootstrap "%s" "%s" "%s"' % (suite, directory, mirror)
        outf.do_command( debootstrap_cmd )
    else:
        debootstrap_cmd = 'debootstrap --foreign --arch=%s "%s" "%s" "%s"' % (target_arch, suite, directory, mirror)
        outf.do_command( debootstrap_cmd )
        outf.do_command( 'cp /usr/bin/%s %s' % (defs["userinterpr"], os.path.join(directory, "usr/bin" )) )
        do_chroot( outf, directory, '/debootstrap/debootstrap --second-stage' )
        do_chroot( outf, directory, 'dpkg --configure -a' )


def mount_stuff( outf, directory ):
    outf.h2( "mounting proc/sys/dev" )
    try:
        outf.do_command( "mount -t proc none %s/proc" % directory )
        outf.do_command( "mount -t sysfs none %s/sys" % directory )
        outf.do_command( "mount -o bind /dev %s/dev" % directory )
        outf.do_command( "mount -o bind /dev/pts %s/dev/pts" % directory )
    except:
        umount_stuff( outf, directory )
        raise


def umount_stuff( outf, directory ):
    outf.h2( "unmounting proc/sys/dev" )
    try:
        outf.do_command( "umount %s/proc" % directory )
    except:
        pass
    try:
        outf.do_command( "umount %s/sys" % directory )
    except:
        pass
    try:
        outf.do_command( "umount %s/dev/pts" % directory )
    except:
        pass
    try:
        outf.do_command( "umount %s/dev" % directory )
    except:
        pass

def do_chroot( outf, directory, cmd, **args ):
    chcmd = "chroot %s %s" % (directory, cmd)
    outf.do_command( chcmd, **args )

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
    os.system( "mkdir -vp "+optelbe_fname )

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

    if not opt.skip_validation:
        if not validate_xml( args[0] ):
            print "xml validation failed. Bailing out"
            sys.exit(20)

    xml = etree( args[0] )
    prj = xml.node("/project")
    tgt = xml.node("/target")

    if not opt.output:
        return 0
    if not opt.target:
        return 0

    opt.target = os.path.abspath(opt.target)

    if opt.buildtype:
        buildtype = opt.buildtype
    elif xml.has( "project/buildtype" ):
        buildtype = xml.text( "/project/buildtype" )
    else:
        buildtype = "nodefaults"

    defs = ElbeDefaults( buildtype )

    chroot = os.path.join(opt.target, "chroot")
    os.system( 'mkdir -p "%s"' % chroot )

    outf = asccidoclog(opt.output)

    if opt.name:
        outf.h1( "ELBE Report for Project "+opt.name )
    else:
        outf.h1( "ELBE Report" )

    outf.printo( "report timestamp: "+datetime.datetime.now().strftime("%Y%m%d-%H%M%S") )

    suite = prj.text("suite")
    target_arch = prj.text("buildimage/arch", default=defs, key="arch")

    slist = ""
    mirror = "Error"
    if prj.has("mirror/primary_host"):
        mirror = "%s://%s/%s" % ( prj.text("mirror/primary_proto"), prj.text("mirror/primary_host").replace("LOCALMACHINE", "10.0.2.2"), prj.text("mirror/primary_path").lstrip("/"))
        slist += "deb %s %s main\n" % (mirror, suite)
        slist += "deb-src %s %s main\n" % (mirror, suite)

    if prj.has("mirror/cdrom"):
        cdrompath = os.path.join( opt.target, "cdrom" )
        mirror = "file://%s/debian" % cdrompath
        os.system( 'mkdir -p "%s"' % cdrompath )
        os.system( 'mount -o loop "%s" "%s"' % (prj.text("mirror/cdrom"), cdrompath ) )

        slist += "deb copy:///mnt %s main\n" % (suite)
        #slist += "deb-src file:///mnt %s main\n" % (suite)

    if opt.proxy:
        os.environ["http_proxy"] = opt.proxy
    elif prj.has("mirror/primary_proxy"):
        os.environ["http_proxy"] = prj.text("mirror/primary_proxy")

    os.environ["LANG"] = "C"
    os.environ["LANGUAGE"] = "C"
    os.environ["LC_ALL"] = "C"
    os.environ["DEBIAN_FRONTEND"]="noninteractive"
    os.environ["DEBONF_NONINTERACTIVE_SEEN"]="true"

    try:
        if prj.node("mirror/url-list"):
            for n in prj.node("mirror/url-list"):
                if n.has("binary"):
                  tmp = n.text("binary").replace("LOCALMACHINE", "10.0.2.2")
                  slist += "deb %s\n" % tmp.strip()
                if n.has("source"):
                  tmp = n.text("source").replace("LOCALMACHINE", "10.0.2.2")
                  slist += "deb-src %s\n" % tmp.strip()

        serial_con, serial_baud = tgt.text( "console" ).split(',')

        if not opt.skip_debootstrap:
            debootstrap( outf, chroot, mirror, suite, target_arch, defs )
        seed_files( outf, chroot, slist, xml, args[0], opt, defs )

    finally:
        if prj.has("mirror/cdrom"):
            os.system( 'umount "%s"' % cdrompath )

    mount_stuff( outf, chroot )
    if prj.has("mirror/cdrom"):
        os.system( 'mount -o loop "%s" "%s"' % (prj.text("mirror/cdrom"), os.path.join(chroot, "mnt")) )

    # sync this with adjustpkgs.py's own list or it will remove packages.
    pkglist = ["parted", "mtd-utils", "dpkg-dev", "dosfstools", "apt-rdepends",
               "python-apt", "rsync", "genisoimage", "reprepro", "python-parted",
               "elbe-daemon"]

    try:
        do_chroot( outf, chroot, "apt-get update" )
        do_chroot( outf, chroot, """/bin/sh -c 'debconf-set-selections < /opt/elbe/custom-preseed.cfg'""" )
        if not opt.skip_debootstrap:
            do_chroot( outf, chroot, "apt-get install -y --force-yes " + string.join( pkglist ) )
        do_chroot( outf, chroot, "elbe adjustpkgs -o /opt/elbe/adjust.log /opt/elbe/source.xml" )
        do_chroot( outf, chroot, """/bin/sh -c 'echo "%s\\n%s\\n" | passwd'""" % (tgt.text("passwd"), tgt.text("passwd")) )
        do_chroot( outf, chroot, """/bin/sh -c 'echo "127.0.0.1 %s %s.%s" >> /etc/hosts'""" % (tgt.text("hostname"), tgt.text("hostname"), tgt.text("domain")) )
        do_chroot( outf, chroot, """/bin/sh -c 'echo "%s" > /etc/hostname'""" % tgt.text("hostname") )
        do_chroot( outf, chroot, """/bin/sh -c 'echo "%s.%s" > /etc/mailname'""" % (tgt.text("hostname"), tgt.text("domain")) )
        do_chroot( outf, chroot, """/bin/sh -c 'echo "T0:23:respawn:/sbin/getty -L %s %s vt100" >> /etc/inittab'""" % (serial_con, serial_baud) )
        do_chroot( outf, chroot, "rm /usr/sbin/policy-rc.d" )
        do_chroot( outf, chroot, "elbe create-target-rfs -t /target --buildchroot /opt/elbe/source.xml" )
        if not opt.skip_cdrom:
            do_chroot( outf, chroot, "/opt/elbe/mkcdrom.sh" )

    finally:
        if prj.has("mirror/cdrom"):
            os.system( 'umount "%s"' % os.path.join(chroot, "mnt") )
        umount_stuff( outf, chroot )

    extract = open( os.path.join(chroot, "opt/elbe/files-to-extract"), "r" )
    for fname in extract.readlines():
        outf.do_command( 'cp "%s" "%s"' % (chroot+fname.strip(), opt.target) ) 
    extract.close()

if __name__ == "__main__":
    run_command( sys.argv[1:] )
