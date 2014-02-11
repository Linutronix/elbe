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

import apt
import apt_pkg
import os
import stat
import sys
import time

from elbepack.version import elbe_version

from tempfile import mkdtemp


def mkdir_p (newdir, mode=0777):
        """works the way a good mkdir -p would...
                - already exists, silently complete
                - regular file in the way, raise an exception
                - parent directory(ies) does not exist, make them as well
        """
        if os.path.isdir (newdir):
                pass
        elif os.path.isfile (newdir):
                raise OSError ("a file with the same name as the desired " \
                               "dir, '%s', already exists." % newdir)
        else:
                os.makedirs (newdir, mode)
                """ mode is not set correctly """
                os.system ("chmod 777 "+newdir)


def touch_file (file):
        if os.path.exists (file):
                os.utime (file, None)
        else:
                file = open (file,"w")
                file.close ()


def get_primary_mirror (project):
        if project.has("mirror/primary_host"):
                m = project.node("mirror")

                mirror = m.text("primary_proto") + "://"
                mirror +=m.text("primary_host")  + "/"
                mirror +=m.text("primary_path")

        elif project.has("mirror/cdrom"):
                 mirror = "file://%s/debian" % cdrompath

        return mirror.replace("LOCALMACHINE", "10.0.2.2")


def create_apt_sources_list (project, rfs_path, log):
        if not project.has("mirror") and not project.has("mirror/cdrom"):
                return "# no mirrors configured"

        if project.has("mirror/primary_host"):
                mirror  = "deb " + get_primary_mirror (project)
                mirror += " " + project.text("suite") + " main\n"

                for url in project.node("mirror/url-list"):
                      if url.has("binary"):
                           mirror += "deb " + url.text("binary").strip() + "\n"
                      if url.has("source"):
                           mirror += "deb-src "+url.text("source").strip()+"\n"

        if project.has("mirror/cdrom"):
                cdrompath = os.path.join( rfs_path, "cdrom" )
                log.do( 'mkdir -p "%s"' % cdrompath )
                log.do( 'mount -o loop "%s" "%s"'
                   % (prj.text("mirror/cdrom"), cdrompath ) )

                mirror += "deb copy:///mnt %s main\n" % (project.text("suite"))

        return mirror.replace("LOCALMACHINE", "10.0.2.2")


class ElbeInstallProgress ():

        def __init__ (self):
                self.write ("init")

        def write (self, line):
                print line

        def start_update (self):
                self.write ("start update")

        def finish_update (self):
                self.write ("finish update")

        def error (self, pkg, errormsg):
                self.write ("Error: " + errormsg)

        def conffile (self, current, new):
                self.write ("conffile question")

        def status_change (self, pkg, percent, status):
                self.write ("status change " + str(percent) + "%")

        def processing (self, pkg, stage):
                self.write ("processing")

        def run (self, obj):
                self.write ("run")
                try:
                    f = os.pipe ()
                    s = os.fdopen (f, "w")
                    obj.do_install (s.fileno)
                except e:
                    self.write ("run failed: " + str (e))
                return 0

class ElbeAcquireProgress (apt.progress.base.AcquireProgress):

        def __init__ (self):
                apt.progress.base.AcquireProgress.__init__ (self)
                self._id = long(1)

        def write (self, line):
                print line

        def start (self):
                apt.progress.base.AcquireProgress.start(self)
                self.write ("start")


        def ims_hit(self, item):
                apt.progress.base.AcquireProgress.ims_hit(self, item)
                line = 'Hit ' + item.description
                if item.owner.filesize:
                    line += ' [%sB]' % apt_pkg.size_to_str(item.owner.filesize)
                self.write (line)


        def fail(self, item):
                apt.progress.base.AcquireProgress.fail(self, item)
                if item.owner.status == item.owner.STAT_DONE:
                        self.write ("Ign " + item.description)
                else:
                        self.write ("Err " + item.description + " " +
                                    item.owner.error_text)


        def fetch(self, item):
                apt.progress.base.AcquireProgress.fetch(self, item)
                if item.owner.complete:
                    return
                item.owner.id = self._id
                self._id += 1
                line = "Get:" + item.owner.id + " " + item.description
                if item.owner.filesize:
                    line += (" [%sB]" % apt_pkg.size_to_str(
                                                        item.owner.filesize))

                self._write(line)


        def pulse (self, owner):
                apt.progress.base.AcquireProgress.pulse(self, owner)
                self.write ("pulse")
                return true


        def stop (self):
                apt.progress.base.AcquireProgress.stop(self)
                self.write ("stop")

class RFS:
        def __init__ (self, xml, defs, log, path="virtual",
                      install_recommends="0"):

                self.in_chroot = 0
                self.xml = xml
                self.project = xml.node ("/project")
                self.target = xml.node ("/target")
                self.full_pkg_list = xml.node ("/fullpkgs")
                self.defs = defs
                self.log = log
                self.rfs_dir = path
                self.cwd = os.open ("/", os.O_RDONLY)

                self.pkg_list = None
                if self.target.has ("pkg-list"):
                    self.pkg_list = self.target.node ("pkg-list")

                self.suite = self.project.text ("suite")

                self.arch = self.project.text(
                   "buildimage/arch", default=defs, key="arch")

                self.host_arch = log.get_command_out(
                  "dpkg --print-architecture").strip ()

                print "host: %s target: %s" % (self.host_arch, self.arch)

                self.primary_mirror = get_primary_mirror (self.project)

                self.virtual = False
                if path == "virtual":
                        self.virtual = True
                        self.rfs_dir = mkdtemp ()
                # TODO think about reinitialization if elbe_version differs
                elif not os.path.isfile(self.rfs_dir + "/etc/elbe_version"):
                        self.debootstrap ()
                else:
                        print 'work on existing rfs'

                self.initialize_dirs ()
                # TODO: self.create_apt_prefs (prefs)


                self.enter_chroot (skip_cache_upd=True)
                # noauth = "0"
                # if project.has("noauth"):
                #         noauth = "1"
                # apt_pkg.config.set ("APT::Get::AllowUnauthenticated", noauth)

                # apt_pkg.config.set ("APT::Install-Recommends",
                #     install_recommends)

                if self.virtual:
                    apt_pkg.config.set ("Dir", self.rfs_dir)
                    apt_pkg.config.set ("Dir::State", "state")
                    apt_pkg.config.set ("Dir::State::status", "status")
                    apt_pkg.config.set ("Dir::Cache", "cache")
                    apt_pkg.config.set ("Dir::Etc", "etc/apt")
                    apt_pkg.config.set ("Dir::Log", "log")

                apt_pkg.config.set ("APT::Architecture", self.arch)
                apt_pkg.config.set ("APT::Cache-Limit", "0")
                apt_pkg.config.set ("APT::Cache-Start", "32505856")
                apt_pkg.config.set ("APT::Cache-Grow", "2097152")

                apt_pkg.init_system()

                self.source = apt_pkg.SourceList ()
                self.source.read_main_list()
                self.cache = apt_pkg.Cache ()
                self.depcache = apt_pkg.DepCache (self.cache)

                if not self.virtual:
                    pkgs = ""
                    for p in self.pkg_list:
                        if p.et.text not in self.cache.packages:
                             pkgs += p.et.text + ", "
                    self.add_pkgs (pkgs)
                    self.leave_chroot ()

                    return

                for p in self.full_pkg_list:
                    if p.et.get('auto') != "true":
                        if p.et.text in self.cache:
                            self.depcache.mark_install (
                                                 self.cache[p.et.text])
                        else:
                            print p.et.text, "not available at mirrors"
                            # TODO throw exception


        def __del__(self):

                if self.virtual:
                        os.system( 'rm -rf "%s"' % self.rfs_dir )

                elif self.host_arch != self.arch:
                        self.log.do( 'rm -f %s' %
                           os.path.join(self.rfs_dir,
                                        "usr/bin"+self.defs["userinterpr"] ))

                if self.project.has ("mirror/cdrom"):
                        cdrompath = os.path.join( self.rfs_path, "cdrom" )
                        self.log.do ('umount "%s"' % cdrompath)

                os.close (self.cwd)


        def verify_with_xml(self):
            for x_pkg in self.full_pkg_list:
                name = x_pkg.et.text
                vers = x_pkg.et.get ('version')
                auto = x_pkg.et.get ('auto')

                if not name in self.cache.packages:
                    if auto == 'false':
                        print name, "doesn't exist in cache, but is used by XML"
                    else:
                        print name, "is no longer required"

                    continue

                cached_p = self.cache[name]

                if cached_p.current_ver:
                    new_p = self.depcache.get_candidate_ver (cached_p)
                    if new_p.ver_str != vers:
                        print name, "version missmatch cache: %s  xml: %s" % (
                              new_p.ver_str, vers)
                else:
                    print name, "is specified in XML but not in cache"


        def dump_xml(self, filename):
            if self.xml.has ("fullpkgs"):
                self.xml.node ("fullpkgs").clear ()
            fpkg = self.xml.ensure_child ("fullpkgs")

            for p in self.cache.packages:
                if p.current_ver:
                    pak = fpkg.append ("pkg")
                    pak.set_text (p.name)
                    pak.et.tail = '\n'
                    pak.et.set ("version", p.current_ver.ver_str)
                    pak.et.set ("md5", str (p.current_ver.hash))
                    if self.depcache.is_auto_installed (p):
                        pak.et.set ("auto", "true")
                    else:
                        pak.et.set ("auto", "false")

            self.xml.write (filename)

        def commit_changes(self, commit=True):
            if not self.virtual and commit:
                self.enter_chroot()
                ret = self.depcache.commit (ElbeAcquireProgress(),
                                            ElbeInstallProgress())
                self.leave_chroot()
                return ret

        def upgrade_rfs(self, commit=True):
                self.enter_chroot ()

                for p in self.cache.packages:
                    cached_p = self.depcache.get_candidate_ver (p.name)
                    if cached_p:
                        if cached_p.ver_str != p.ver_str:
                            print "upgr. %s to version %s" % (cached_p.name,
                                                              cached_p.ver_str)
                            self.depcache.mark_install (cached_p)
                    else:
                        print "%s is no longer available in apt" % (p.name)

                self.commit_changes (commit)
                self.leave_chroot ()


        def get_pkg_list(self):
                self.enter_chroot ()
                pl = ""
                for p in self.cache.packages:
                    if p.current_state == apt_pkg.CURSTATE_INSTALLED:
                        pl += p.name + ", "

                self.leave_chroot ()
                return pl


        def add_pkgs(self, pkgs, commit=True):
                self.enter_chroot ()

                p_list = pkgs.split(",")
                for pkg in p_list:
                    if pkg.strip() != "":
                        try:
                            p = self.cache[pkg.strip()]
                            print p.name
                            self.depcache.mark_install (p)
                        except:
                            print pkg.strip(), "not found in cache"

                self.commit_changes (commit)
                self.leave_chroot ()


        def remove_pkgs(self, pkgs, commit=True):
                self.enter_chroot ()

                p_list = pkgs.split(",")
                for pkg in p_list:
                    p = self.cache[pkg.strip()]
                    print p.name
                    self.depcache.mark_delete (p, True)

                self.commit_changes (commit)
                self.leave_chroot ()


        def autoremove_pkgs(self, commit=True):
                self.enter_chroot ()

                for p in self.cache.packages:
                    if self.depcache.is_garbage(p):
                        print p.name
                        self.depcache.mark_delete (p, True)

                self.commit_changes (commit)
                self.leave_chroot ()


        def umount (self):
                try:
                    self.log.do("umount %s/proc/sys/fs/binfmt_misc" % (
                                self.rfs_dir))
                except:
                    pass
                try:
                    self.log.do("umount %s/proc" % self.rfs_dir)
                except:
                    pass
                try:
                    self.log.do("umount %s/sys" % self.rfs_dir)
                except:
                    pass
                try:
                    self.log.do("umount %s/dev/pts" % self.rfs_dir)
                except:
                    pass
                try:
                    self.log.do("umount %s/dev" % self.rfs_dir)
                except:
                    pass


        def update_cache(self):
                try:
                    self.cache.update (ElbeAcquireProgress(),
                                       self.source, 1000)
                except:
                    pass


        def enter_chroot (self, skip_cache_upd=False):
                if self.virtual:
                    if not skip_cache_upd:
                        self.update_cache ()
                    return

                if self.in_chroot:
                    self.in_chroot += 1
                    return

                try:
                    self.log.do("mount -t proc none %s/proc" % self.rfs_dir)
                    self.log.do("mount -t sysfs none %s/sys" % self.rfs_dir)
                    self.log.do("mount -o bind /dev %s/dev" % self.rfs_dir)
                    self.log.do("mount -o bind /dev/pts %s/dev/pts" % (
                                self.rfs_dir))
                except:
                    self.umount ()
                    raise

                os.chroot(self.rfs_dir)

                if not skip_cache_upd:
                    self.update_cache ()

                os.environ["LANG"] = "C"
                os.environ["LANGUAGE"] = "C"
                os.environ["LC_ALL"] = "C"

                self.in_chroot = 1

        def leave_chroot (self):
                if self.virtual:
                    return

                if self.in_chroot > 1:
                    self.in_chroot -= 1
                    return

                os.fchdir (self.cwd)
                os.chroot(".")
                self.umount ()

                self.in_chroot = 0


        def write_version (self):
                f = file(os.path.join(self.rfs_dir, "etc/elbe_version"), "w+")

                f.write("%s %s\n" % (self.project.text("name"),
                                   self.project.text("version")))

                f.write("this RFS was generated by elbe %s\n" % (elbe_version))
                f.write(time.strftime("%c"))

                f.close()


        def debootstrap (self):
                if self.project.has("mirror/primary_proxy"):
                        os.environ["http_proxy"] = self.project.text(
                                                     "mirror/primary_proxy")

                os.environ["LANG"] = "C"
                os.environ["LANGUAGE"] = "C"
                os.environ["LC_ALL"] = "C"
                os.environ["DEBIAN_FRONTEND"]="noninteractive"
                os.environ["DEBONF_NONINTERACTIVE_SEEN"]="true"

                self.log.h2( "debootstrap log" )

                if self.host_arch == self.arch:
                    cmd = 'debootstrap "%s" "%s" "%s"' % (
                                self.suite, self.rfs_dir, self.primary_mirror)

                    self.log.do( cmd )

                    return

                cmd = 'debootstrap --foreign --arch=%s "%s" "%s" "%s"' % (
                    self.arch, self.suite, self.rfs_dir, self.primary_mirror)

                self.log.do (cmd)

                self.log.do ('cp /usr/bin/%s %s' % (self.defs["userinterpr"],
                    os.path.join(self.rfs_dir, "usr/bin" )) )

                self.log.chroot (self.rfs_dir,
                                 '/debootstrap/debootstrap --second-stage')

                self.log.chroot (self.rfs_dir, 'dpkg --configure -a')

                self.write_version ()


        def start (self):
                pass

        def stop (self):
                pass

        def pulse (self, obj):
                #print "updating in progress", obj
                return True


        def initialize_dirs (self):
                mkdir_p (self.rfs_dir + "/cache/archives/partial")
                mkdir_p (self.rfs_dir + "/etc/apt/preferences.d")
                mkdir_p (self.rfs_dir + "/db")
                mkdir_p (self.rfs_dir + "/log")
                mkdir_p (self.rfs_dir + "/state/lists/partial")
                touch_file (self.rfs_dir + "/state/status")

                mirror = create_apt_sources_list (
                                self.project, self.rfs_dir, self.log)

                sources_list = self.rfs_dir + "/etc/apt/sources.list"

                if os.path.exists (sources_list):
                        os.remove (sources_list)

                sl_file = open (sources_list, "w")
                sl_file.write (mirror)
                sl_file.close ()


        def create_apt_prefs (self, prefs):
                filename = self.rfs_dir + "/etc/apt/preferences"

                if os.path.exists (filename):
                        os.remove (filename)

                file = open (filename,"w")
                file.write (prefs)
                file.close ()
