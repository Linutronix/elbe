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
import cPickle
import os
import stat
import sys
import time

from tempfile import mkdtemp
from tempfile import mktemp

from elbepack.version import elbe_version
from elbepack.aptprogress import ElbeAcquireProgress, ElbeInstallProgress

# XXX mount the cdrom image 
#                    cdrompath = os.path.join( rfs_path, "cdrom" )
#                    log.do( 'mkdir -p "%s"' % cdrompath )
#                    log.do( 'mount -o loop "%s" "%s"'
#                       % (prj.text("mirror/cdrom"), cdrompath ) )


class ChrootReturn(Exception):
    def __init__(self, val):
        self.val = val

class InChroot(object):
    def __init__ (self, rfs, log, callback=None):
        self.rfs = rfs
        self.log = log
        self.callback = None

    def __enter__ (self):
        self.pipe1, self.pipe2 = Pipe()
        pid = os.fork ()
        if (pid):
            while True:
                x = self.pipe1.recv()
                if isinstance(x,Exception):
                    os.waitpid (pid, 0)
                    raise x
                elif self.callback:
                    self.callback(x)
        try:
            self.rfs.enter_chroot (self.log)
        except:
            self.pipe2.send(sys.exc_info () [1] )
            return None

        return self.pipe2


    def __exit__(self, type, value, traceback):
        if traceback:
            self.pipe2.send(value)
        else:
            self.pipe2.send(ChrootReturn(None))

        self.rfs.leave_chroot (self.log)
        sys.exit ()

# This is a workaround, the DepCache behaviour during pickle.load ()
#
# >>> dc = cPickle.load (fd)
# Reading package lists... Done
# Building dependency tree
# Reading state information... Done
# Traceback (most recent call last):
#   File "<stdin>", line 1, in <module>
# TypeError: Required argument 'cache' (pos 1) not found
#
class ElbeDepCache:
        apt_dep = None
        def __init__ (self, cache, real_init=False):
            if (real_init):
                print 'real_init'
                apt_dep = apt_pkg.DepCache.__init__ (cache)

class RFS:
        depcache = None
        cache = None
        source = None

        def __init__ (self, path, arch):
                self.path = path
                self.arch = arch
                self.cwd = os.open ("/", os.O_RDONLY)
        def __delete__ (self):
                os.close (self.cwd)

class BuildEnv (RFS):
        def __init__ (self, xml, log, path ):

                self.xml = xml
                self.log = log

                self.rfs = BuildImgFs( path )


                # TODO think about reinitialization if elbe_version differs
                if not self.rfs.isfile( "etc/elbe_version" ):
                        self.debootstrap ()
                else:
                        print 'work on existing rfs'

                self.initialize_dirs ()
                # TODO: self.create_apt_prefs (prefs)




        def __del__(self):

                if self.host_arch != self.rfs.arch:
                        self.log.do( 'rm -f %s' %
                           os.path.join(self.rfs.path,
                                        "usr/bin"+self.defs["userinterpr"] ))

                if self.project.has ("mirror/cdrom"):
                        cdrompath = os.path.join( self.rfs.path, "cdrom" )
                        self.log.do ('umount "%s"' % cdrompath)



        def debootstrap (self):

                suite = self.xml.prj.text ("suite")

                host_arch = self.log.get_command_out(
                  "dpkg --print-architecture").strip ()

                arch = self.xml.text("project/buildimage/arch", key="arch")

                print "host: %s target: %s" % (self.host_arch, arch)

                primary_mirror = self.xml.get_primary_mirror()
                if self.project.has("mirror/primary_proxy"):
                        os.environ["http_proxy"] = self.project.text(
                                                     "mirror/primary_proxy")

                os.environ["LANG"] = "C"
                os.environ["LANGUAGE"] = "C"
                os.environ["LC_ALL"] = "C"
                os.environ["DEBIAN_FRONTEND"]="noninteractive"
                os.environ["DEBONF_NONINTERACTIVE_SEEN"]="true"

                self.log.h2( "debootstrap log" )

                if host_arch == arch:
                    cmd = 'debootstrap "%s" "%s" "%s"' % (
                                suite, self.rfs.path, primary_mirror)

                    self.log.do( cmd )

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


        def initialize_dirs (self):
                mkdir_p (self.rfs.path + "/cache/archives/partial")
                mkdir_p (self.rfs.path + "/etc/apt/preferences.d")
                mkdir_p (self.rfs.path + "/db")
                mkdir_p (self.rfs.path + "/log")
                mkdir_p (self.rfs.path + "/state/lists/partial")
                touch_file (self.rfs.path + "/state/status")

                mirror = create_apt_sources_list (
                                self.project, self.rfs.path, self.log)

                sources_list = self.rfs.path + "/etc/apt/sources.list"

                if os.path.exists (sources_list):
                        os.remove (sources_list)

                write_file (sources_list, 644, mirror)


        def create_apt_prefs (self, prefs):
                filename = self.rfs.path + "/etc/apt/preferences"

                if os.path.exists (filename):
                        os.remove (filename)

                file = open (filename,"w")
                file.write (prefs)
                file.close ()



class PkgStuff(BuildEnv):
        def __init__ (self, xml, log, path ):
                BuildEnv.__init__(self, xml, log, path)

                try:
                    with InChroot (self.rfs, self.log) as handle:
                        # noauth = "0"
                        # if project.has("noauth"):
                        #         noauth = "1"
                        # apt_pkg.config.set ("APT::Get::AllowUnauthenticated",
                        #                     noauth)
                        # apt_pkg.config.set ("APT::Install-Recommends",
                        #                     install_recommends)

                        apt_pkg.config.set ("APT::Cache-Limit", "0")
                        apt_pkg.config.set ("APT::Cache-Start", "32505856")
                        apt_pkg.config.set ("APT::Cache-Grow", "2097152")

                        apt_pkg.config.set ("APT::Architecture",
                                            handle.rfs.arch)

                        apt_pkg.init_system()

                        sl = apt_pkg.SourceList ()
                        sl.read_main_list()
                        ca = apt_pkg.Cache()
                        dc = ElbeDepCache (handle.rfs.cache, real_init=True)

                        handle.send( ChrootReturn( (sl,ca,dc) ) )

                        print ca
                except ChrootReturn as ret:
                    self.rfs.source = ret.value[0]
                    self.rfs.cache = ret.value[1]
                    self.rfs.depcache = ret.value[2]

                pkgs = ""
                for p in self.pkg_list:
                    if p.et.text not in self.rfs.cache.packages:
                         pkgs += p.et.text + ", "

                self.add_pkgs (pkgs)
                self.commit ()

                # TODO split code out to enable installation of specified
                #      versions into real systems (udpated)
                #for p in self.full_pkg_list:
                #    if p.et.get('auto') != "true":
                #        if p.et.text in self.rfs.cache:
                #            self.rfs.depcache.mark_install (
                #                                 self.rfs.cache[p.et.text])
                #        else:
                #            print p.et.text, "not available at mirrors"
                #            # TODO throw exception

        def verify_with_xml(self):
            for x_pkg in self.full_pkg_list:
                name = x_pkg.et.text
                vers = x_pkg.et.get ('version')
                auto = x_pkg.et.get ('auto')

                if not name in self.rfs.cache.packages:
                    if auto == 'false':
                        print name, "doesn't exist in cache, but is used by XML"
                    else:
                        print name, "is no longer required"

                    continue

                cached_p = self.rfs.cache[name]

                if cached_p.current_ver:
                    new_p = self.rfs.depcache.get_candidate_ver (cached_p)
                    if new_p.ver_str != vers:
                        print name, "version missmatch cache: %s  xml: %s" % (
                              new_p.ver_str, vers)
                else:
                    print name, "is specified in XML but not in cache"


        def dump_xml(self, filename):
            if self.xml.has ("fullpkgs"):
                self.xml.node ("fullpkgs").clear ()
            fpkg = self.xml.ensure_child ("fullpkgs")

            for p in self.rfs.cache.packages:
                if p.current_ver:
                    pak = fpkg.append ("pkg")
                    pak.set_text (p.name)
                    pak.et.tail = '\n'
                    pak.et.set ("version", p.current_ver.ver_str)
                    pak.et.set ("md5", str (p.current_ver.hash))
                    if self.rfs.depcache.is_auto_installed (p):
                        pak.et.set ("auto", "true")
                    else:
                        pak.et.set ("auto", "false")

            self.xml.write (filename)


        def commit (self):
            try:
                with InChroot (self.rfs, self.log) as handle:
                    handle.return_code = handle.rfs.depcache.apt_dep.commit (
                                                    ElbeAcquireProgress(),
                                                    ElbeInstallProgress())
                    # cache needs to be reopened,
                    # else commited changes cannot be seen in the cache
                    handle.rfs.cache = apt_pkg.Cache ()
                    handle.rfs.depcache = ElbeDepCache (handle.rfs.cache, True)

            except ChrootReturn as ret:
                self.rfs = ret.rfs
                rc = ret.code
                if ret.exception_type:
                    print ('exception occured: ',
                           ret.exception_type, ret.exception)
                    raise ret

            return rc


        def upgrade (self):
            try:
                with InChroot (self.rfs, self.log) as handle:
                    handle.return_code = []
                    for p in handle.rfs.cache.packages:
                        cached_p = handle.rfs.depcache.get_candidate_ver (p.name)
                        if cached_p:
                            if cached_p.ver_str != p.ver_str:
                                print "upgr. %s to version %s" % (cached_p.name,
                                                                  cached_p.ver_str)
                                handle.rfs.depcache.mark_install (cached_p)
                                handle.return_code.append (cached_p)
                        else:
                            print "%s is no longer available in apt" % (p.name)

            except ChrootReturn as ret:
                self.rfs = ret.rfs
                rc = ret.code
                if ret.exception_type:
                    print ('exception occured: ',
                           ret.exception_type, ret.exception)
                    raise ret

            return rc

        def get_pkg_list (self):
            try:
                with InChroot (self.rfs, self.log) as handle:
                    handle.return_code = []
                    for p in self.rfs.cache.packages:
                        if p.current_state == apt_pkg.CURSTATE_INSTALLED:
                            handle.return_code.append (p)
            except ChrootReturn as ret:
                self.rfs = ret.rfs
                rc = ret.code
                if ret.exception_type:
                    print ('exception occured: ',
                           ret.exception_type, ret.exception)
                    raise ret

            return rc


        def add_pkgs (self, pkgs):
            try:
                with InChroot (self.rfs, self.log) as handle:

                    p_list = pkgs.split(",")
                    for pkg in p_list:
                        if pkg.strip() != "":
                            try:
                                p = handle.rfs.cache[pkg.strip()]
                                print "INSTALL", p.name
                                handle.rfs.depcache.mark_install (p)
                            except:
                                print pkg.strip(), "not found in cache"

            except ChrootReturn as ret:
                self.rfs = ret.rfs
                if ret.exception_type:
                    print ('exception occured: ',
                           ret.exception_type, ret.exception)
                    raise ret


        def remove_pkgs (self, pkgs):
            try:
                with InChroot (self.rfs, self.log) as handle:

                    p_list = pkgs.split(",")
                    for pkg in p_list:
                        p = handle.rfs.cache[pkg.strip()]
                        print "REMOVE", p.name
                        handle.rfs.depcache.mark_delete (p, True)

            except ChrootReturn as ret:
                self.rfs = ret.rfs
                if ret.exception_type:
                    print ('exception occured: ',
                           ret.exception_type, ret.exception)
                    raise ret


        def autoremove_pkgs (self):
            try:
                with InChroot (self.rfs, self.log) as handle:

                    for p in handle.rfs.cache.packages:
                        if handle.rfs.depcache.is_garbage(p):
                            print "AUTOREMOVE", p.name
                            handle.rfs.depcache.mark_delete (p, True)

            except ChrootReturn as ret:
                self.rfs = ret.rfs
                if ret.exception_type:
                    print ('exception occured: ',
                           ret.exception_type, ret.exception)
                    raise ret


        def update_cache (self):
            try:
                with InChroot (self.rfs, self.log) as handle:
                    handle.rfs.cache.update (ElbeAcquireProgress(),
                                             handle.rfs.source, 1000)

                    # cache needs to be reopened,
                    # else commited changes cannot be seen in the cache
                    handle.rfs.cache = apt_pkg.Cache ()
                    handle.rfs.depcache = apt_pkg.DepCache (handle.rfs.cache)

            except ChrootReturn as ret:
                self.rfs = ret.rfs
                if ret.exception_type:
                    print ('exception occured: ',
                           ret.exception_type, ret.exception)
                    raise ret

