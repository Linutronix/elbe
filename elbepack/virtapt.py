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

# don't remove the apt import, it is really needed, due to some magic in apt_pkg
import apt

from tempfile import mkdtemp


class VirtApt:
    def __init__ (self, name, arch, suite, sources, prefs):

        self.projectpath = mkdtemp()
        self.initialize_dirs ()

        self.create_apt_sources_list (sources)
        self.create_apt_prefs        (prefs)

        apt_pkg.config.set ("APT::Architecture", arch)
        apt_pkg.config.set ("Acquire::http::Proxy::127.0.0.1", "DIRECT")
        apt_pkg.config.set ("APT::Install-Recommends", "0")
        apt_pkg.config.set ("Dir", self.projectpath)
        apt_pkg.config.set ("APT::Cache-Limit", "0")
        apt_pkg.config.set ("APT::Cache-Start", "32505856")
        apt_pkg.config.set ("APT::Cache-Grow", "2097152")
        apt_pkg.config.set ("Dir::State", "state")
        apt_pkg.config.set ("Dir::State::status", "status")
        apt_pkg.config.set ("Dir::Cache", "cache")
        apt_pkg.config.set ("Dir::Etc", "etc/apt")
        apt_pkg.config.set ("Dir::Log", "log")
        apt_pkg.config.set ("APT::Get::AllowUnauthenticated", "1")

        apt_pkg.init_system()

        self.source = apt_pkg.SourceList ()
        self.source.read_main_list()
        self.cache = apt_pkg.Cache ()
        try:
            self.cache.update(self,self.source)
        except:
            pass

        apt_pkg.config.set ("APT::Default-Release", suite)

        self.cache = apt_pkg.Cache ()
        try:
            self.cache.update(self,self.source)
        except:
            pass

    def __del__(self):
        os.system( 'rm -rf "%s"' % self.projectpath )

    def start (self):
        pass

    def stop (self):
        pass

    def pulse (self, obj):
        #print "updating in progress", obj
        return True

    def mkdir_p (self, newdir, mode=0777):
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

    def touch (self, file):
        if os.path.exists (file):
            os.utime (file, None)
        else:
            file = open (file,"w")
            file.close ()

    def initialize_dirs (self):
        self.mkdir_p (self.projectpath + "/cache/archives/partial")
        self.mkdir_p (self.projectpath + "/etc/apt/preferences.d")
        self.mkdir_p (self.projectpath + "/db")
        self.mkdir_p (self.projectpath + "/log")
        self.mkdir_p (self.projectpath + "/state/lists/partial")
        self.touch   (self.projectpath + "/state/status")

    def create_apt_sources_list (self, mirror):
        filename = self.projectpath + "/etc/apt/sources.list"

        if os.path.exists (filename):
            os.remove (filename)

        file = open (filename,"w")
        file.write (mirror)
        file.close ()

    def create_apt_prefs (self, prefs):
        filename = self.projectpath + "/etc/apt/preferences"

        if os.path.exists (filename):
            os.remove (filename)

        file = open (filename,"w")
        file.write (prefs)
        file.close ()

