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
import urlparse

import elbepack

from elbepack.aptprogress import ElbeAcquireProgress, ElbeInstallProgress
from elbepack.filesystem import BuildImgFs
from elbepack.templates import write_pack_template, get_preseed, preseed_to_text


class BuildEnv ():
    def __init__ (self, xml, log, path ):

        self.xml = xml
        self.log = log

        self.rfs = BuildImgFs (path, xml.defs["userinterpr"])

        # TODO think about reinitialization if elbe_version differs
        if not self.rfs.isfile( "etc/elbe_version" ):
            # avoid starting daemons inside the buildenv
            self.rfs.mkdir_p ("usr/sbin")
            self.rfs.write_file ("usr/sbin/policy-rc.d",
                0755, "#!/bin/sh\nexit 101\n")
            self.debootstrap ()
            self.fresh_debootstrap = True
            self.need_dumpdebootstrap = True
        else:
            print 'work on existing rfs'
            self.fresh_debootstrap = False
            self.need_dumpdebootstrap = False

        self.initialize_dirs ()

    def cdrom_umount(self):
        if self.xml.prj.has ("mirror/cdrom"):
            cdrompath = self.rfs.fname( "cdrom" )
            self.log.do ('umount "%s"' % cdrompath)

    def cdrom_mount(self):
        if self.xml.has("project/mirror/cdrom"):
            cdrompath = self.rfs.fname("cdrom")
            self.log.do( 'mkdir -p "%s"' % cdrompath )
            self.log.do( 'mount -o loop "%s" "%s"'
               % (self.xml.text("project/mirror/cdrom"), cdrompath ) )

    def __enter__(self):
        self.cdrom_mount()
        self.rfs.__enter__()
        return self

    def __exit__(self, type, value, traceback):
        self.rfs.__exit__(type, value, traceback)
        self.cdrom_umount()

    def debootstrap (self):

        suite = self.xml.prj.text ("suite")

        primary_mirror = self.xml.get_primary_mirror(self.rfs.fname('cdrom') )

        if self.xml.prj.has("mirror/primary_proxy"):
            os.environ["no_proxy"] = "10.0.2.2,localhost,127.0.0.1"
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

        host_arch = self.log.get_command_out(
                "dpkg --print-architecture").strip ()

        if not self.xml.is_cross (host_arch):
            if self.xml.has("project/noauth"):
                cmd = 'debootstrap --no-check-gpg --arch=%s "%s" "%s" "%s"' % (
                            arch, suite, self.rfs.path, primary_mirror)
            else:
                cmd = 'debootstrap --arch=%s "%s" "%s" "%s"' % (
                            arch, suite, self.rfs.path, primary_mirror)

            try:
                self.cdrom_mount()
                self.log.do( cmd )
            finally:
                self.cdrom_umount()

            return

        if self.xml.has("project/noauth"):
            cmd = 'debootstrap --no-check-gpg --foreign --arch=%s "%s" "%s" "%s"' % (
                arch, suite, self.rfs.path, primary_mirror)
        else:
            cmd = 'debootstrap --foreign --arch=%s "%s" "%s" "%s"' % (
                arch, suite, self.rfs.path, primary_mirror)

        try:
            self.cdrom_mount()
            self.log.do (cmd)

            ui = "/usr/share/elbe/qemu-elbe/" + self.xml.defs["userinterpr"]

            if not os.path.exists (ui):
                ui = "/usr/bin/" + self.xml.defs["userinterpr"]

            self.log.do ('cp %s %s' % (ui, self.rfs.fname( "usr/bin" )))

            self.log.chroot (self.rfs.path,
                             '/debootstrap/debootstrap --second-stage')

            self.log.chroot (self.rfs.path, 'dpkg --configure -a')

        finally:
            self.cdrom_umount()


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

        self.rfs.write_file ("etc/apt/sources.list", 0644, mirror)

        self.rfs.mkdir_p( "var/cache/elbe" )

        preseed = get_preseed( self.xml )
        preseed_txt = preseed_to_text( preseed )
        self.rfs.write_file( "var/cache/elbe/preseed.txt", 0644, preseed_txt )
        with self.rfs:
            self.log.chroot( self.rfs.path, 'debconf-set-selections < %s' % self.rfs.fname("var/cache/elbe/preseed.txt") )


    def create_apt_prefs (self):

        filename = self.rfs.path + "/etc/apt/preferences"

        if os.path.exists (filename):
            os.remove (filename)

        self.rfs.mkdir_p ("/etc/apt")

        pinned_origins = []
        if self.xml.has('project/mirror/url-list'):
            for url in self.xml.node('project/mirror/url-list'):
                if not url.has('binary'):
                    continue

                repo = url.node('binary')
                if not 'pin' in repo.et.attrib:
                    continue

                origin = urlparse.urlsplit(repo.et.text.strip()).hostname
                pin = repo.et.attrib['pin']
                if 'package' in repo.et.attrib:
                    package = repo.et.attrib['package']
                else:
                    package = '*'
                pinning = { 'pin':     pin,
                            'origin':  origin,
                            'package': package }
                pinned_origins.append(pinning)

        d = { "xml":   self.xml,
              "prj":   self.xml.node("/project"),
              "pkgs":  self.xml.node("/target/pkg-list"),
              "porgs": pinned_origins }

        write_pack_template( filename, "preferences.mako", d )

    def seed_etc( self ):
        passwd = self.xml.text("target/passwd")
        self.log.chroot( self.rfs.path,
             """/bin/sh -c 'echo "%s\\n%s\\n" | passwd'""" % (passwd, passwd) )

        hostname = self.xml.text("target/hostname")
        domain = self.xml.text("target/domain")

        self.log.chroot( self.rfs.path, """/bin/sh -c 'echo "127.0.0.1 %s.%s %s elbe-daemon" >> /etc/hosts'""" % (hostname, domain, hostname) )
        self.log.chroot( self.rfs.path, """/bin/sh -c 'echo "%s" > /etc/hostname'""" % hostname )
        self.log.chroot( self.rfs.path, """/bin/sh -c 'echo "%s.%s" > /etc/mailname'""" % (hostname, domain) )

        serial_con, serial_baud = self.xml.text( "target/console" ).split(',')
        if serial_baud:
            self.log.chroot(self.rfs.path, """/bin/sh -c 'echo "T0:23:respawn:/sbin/getty -L %s %s vt100" >> /etc/inittab'""" % (serial_con, serial_baud) )
        else:
            self.log.printo("parsing console tag failed, needs to be of '/dev/ttyS0,115200' format.")
