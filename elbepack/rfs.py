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

import apt_pkg
import os
import sys

import elbepack

from elbepack.aptprogress import ElbeAcquireProgress, ElbeInstallProgress
from elbepack.filesystem import BuildImgFs

from multiprocessing import Pipe

from mako.template import Template
from mako import exceptions

# XXX mount the cdrom image
#                    cdrompath = os.path.join( rfs_path, "cdrom" )
#                    log.do( 'mkdir -p "%s"' % cdrompath )
#                    log.do( 'mount -o loop "%s" "%s"'
#                       % (prj.text("mirror/cdrom"), cdrompath ) )


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

class BuildEnv ():
    def __init__ (self, xml, log, path ):

        self.xml = xml
        self.log = log

        self.rfs = BuildImgFs (path, xml.defs["userinterpr"])
        self.host_arch = self.log.get_command_out(
                              "dpkg --print-architecture").strip ()

        # TODO think about reinitialization if elbe_version differs
        if not self.rfs.isfile( "etc/elbe_version" ):
            self.debootstrap ()
        else:
            print 'work on existing rfs'

        self.initialize_dirs ()




    def __del__(self):
        if self.xml.prj.has ("mirror/cdrom"):
            cdrompath = os.path.join( self.rfs.path, "cdrom" )
            self.log.do ('umount "%s"' % cdrompath)

    def debootstrap (self):

        suite = self.xml.prj.text ("suite")

        primary_mirror = self.xml.get_primary_mirror(
                                           self.rfs.fname('cdrom') )

        if self.xml.prj.has("mirror/primary_proxy"):
            os.environ["http_proxy"] = self.xml.prj.text(
                    "mirror/primary_proxy")

        os.environ["LANG"] = "C"
        os.environ["LANGUAGE"] = "C"
        os.environ["LC_ALL"] = "C"
        os.environ["DEBIAN_FRONTEND"]="noninteractive"
        os.environ["DEBONF_NONINTERACTIVE_SEEN"]="true"

        self.log.h2( "debootstrap log" )

        self.create_apt_prefs ()

        arch = self.xml.text ("project/buildimage/arch", key="arch")

        if not self.xml.is_cross (self.host_arch):
            cmd = 'debootstrap --arch=%s "%s" "%s" "%s"' % (
                        arch, suite, self.rfs.path, primary_mirror)

            self.log.do( cmd )
            try:
                self.rfs.dump_elbeversion (self.xml)
            except:
                self.log.printo ("dump elbeversion failed")

            return

        cmd = 'debootstrap --foreign --arch=%s "%s" "%s" "%s"' % (
            arch, suite, self.rfs.path, primary_mirror)

        self.log.do (cmd)

        self.log.do ('cp /usr/bin/%s %s' % (self.xml.defs["userinterpr"],
            self.rfs.fname( "usr/bin" )) )

        self.log.chroot (self.rfs.path,
                         '/debootstrap/debootstrap --second-stage')

        self.log.chroot (self.rfs.path, 'dpkg --configure -a')

        self.rfs.dump_elbeversion (self.xml)


    def virtapt_init_dirs(self):
        mkdir_p (self.rfs.path + "/cache/archives/partial")
        mkdir_p (self.rfs.path + "/etc/apt/preferences.d")
        mkdir_p (self.rfs.path + "/db")
        mkdir_p (self.rfs.path + "/log")
        mkdir_p (self.rfs.path + "/state/lists/partial")
        touch_file (self.rfs.path + "/state/status")

    def initialize_dirs (self):
        mirror = self.xml.create_apt_sources_list ()

        if self.rfs.exists("etc/apt/sources.list"):
            self.rfs.remove("etc/apt/sources.list")

        self.rfs.write_file ("etc/apt/sources.list", 644, mirror)


    def create_apt_prefs (self):

        filename = self.rfs.path + "/etc/apt/preferences"

        if os.path.exists (filename):
            os.remove (filename)

        self.rfs.mkdir_p ("/etc/apt")

        d = { "xml":  self.xml,
              "prj":  self.xml.node("/project"),
              "pkgs": self.xml.node("/target/pkg-list") }

        write_template( filename, "preferences.mako", d )

    def seed_etc( self ):
        passwd = self.xml.text("target/passwd")
        self.log.chroot( self.rfs.path, """/bin/sh -c 'echo "%s\\n%s\\n" | passwd'""" % (passwd, passwd) )

        hostname = self.xml.text("target/hostname")
        domain = self.xml.text("target/domain")

        self.log.chroot( self.rfs.path, """/bin/sh -c 'echo "127.0.0.1 %s %s.%s" >> /etc/hosts'""" % (hostname, hostname, domain) )
        self.log.chroot( self.rfs.path, """/bin/sh -c 'echo "%s" > /etc/hostname'""" % hostname )
        self.log.chroot( self.rfs.path, """/bin/sh -c 'echo "%s.%s" > /etc/mailname'""" % (hostname, domain) )

        serial_con, serial_baud = self.xml.text( "target/console" ).split(',')
        self.log.chroot( self.rfs.path, """/bin/sh -c 'echo "T0:23:respawn:/sbin/getty -L %s %s vt100" >> /etc/inittab'""" % (serial_con, serial_baud) )
