# ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (c) 2013-2018 Manuel Traut <manut@linutronix.de>
# Copyright (c) 2014-2015, 2018 Torben Hohn <torben.hohn@linutronix.de>
# Copyright (c) 2018 John Ogness <john.ogness@linutronix.de>
# Copyright (c) 2018 Oliver Brandt <oliver.brandt@lenze.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import print_function

import apt_pkg
import os
import sys

# don't remove the apt import, it is really needed, due to some magic in
# apt_pkg
import apt

from tempfile import mkdtemp
from multiprocessing.managers import BaseManager

from elbepack.shellhelper import CommandError, system
from elbepack.directories import elbe_pubkey_fname


def getdeps(pkg):
    for dd in pkg.depends_list.get("Depends", []):
        for d in dd:
            yield d.target_pkg.name


# target_pkg is either a 'package name' or a 'provides'
#
# ATTENTION: for provides pinning and priorities for package selection are
#            ignored. This should be safe for now, because the code is only
#            used for downloading 'elbe-bootstrap' and generating the SDKs
#            host-sysroot. For generating host-sysroots there is no posibility
#            to modify package priorities via elbe-xml.
def lookup_uri(v, d, target_pkg):
    try:
        pkg = v.cache[target_pkg]
        c = d.get_candidate_ver(pkg)
    except KeyError:
        pkg = None
        c = None

    if not c:
        for pkg in v.cache.packages:
            for x in pkg.provides_list:
                if target_pkg == x[0]:
                    return lookup_uri(v, d, x[2].parent_pkg.name)
        return "", "", ""

    x = v.source.find_index(c.file_list[0][0])

    r = apt_pkg.PackageRecords(v.cache)
    r.lookup(c.file_list[0])
    uri = x.archive_uri(r.filename)

    if not x.is_trusted:
        return target_pkg, uri, ""

    try:
        hashval = str(r.hashes.find('SHA256')).split(':')[1]
    except AttributeError:
        # TODO: this fallback Code can be removed on stretch
        #       but it throws DeprecationWarning already
        hashval = r.sha256_hash

    return target_pkg, uri, hashval



class VirtApt:
    def __init__(self, arch, suite, sources, prefs, keylist=[], noauth=False):

        # pylint: disable=too-many-arguments

        self.projectpath = mkdtemp()
        self.initialize_dirs()

        self.create_apt_sources_list(sources)
        self.create_apt_prefs(prefs)
        self.setup_gpg()
        for k in keylist:
            self.add_pubkey_url(k)

        apt_pkg.config.set("APT::Architecture", arch)
        apt_pkg.config.set("APT::Architectures", arch)
        apt_pkg.config.set("Acquire::http::Proxy::127.0.0.1", "DIRECT")
        apt_pkg.config.set("APT::Install-Recommends", "0")
        apt_pkg.config.set("Dir::Etc", self.projectpath)
        apt_pkg.config.set("APT::Cache-Limit", "0")
        apt_pkg.config.set("APT::Cache-Start", "32505856")
        apt_pkg.config.set("APT::Cache-Grow", "2097152")
        apt_pkg.config.set("Dir::State", os.path.join(self.projectpath, "state"))
        apt_pkg.config.set("Dir::State::status", os.path.join(self.projectpath, "state/status"))
        apt_pkg.config.set("Dir::Cache", os.path.join(self.projectpath, "cache"))
        apt_pkg.config.set("Dir::Cache::archives", os.path.join(self.projectpath, "cache/archives"))
        apt_pkg.config.set("Dir::Etc", os.path.join(self.projectpath, "etc/apt"))
        apt_pkg.config.set("Dir::Log", os.path.join(self.projectpath, "log"))
        if noauth:
            apt_pkg.config.set("APT::Get::AllowUnauthenticated", "1")
            apt_pkg.config.set("Acquire::AllowInsecureRepositories", "1")
        else:
            apt_pkg.config.set("APT::Get::AllowUnauthenticated", "0")
            apt_pkg.config.set("Acquire::AllowInsecureRepositories", "0")

        apt_pkg.init_system()

        self.source = apt_pkg.SourceList()
        self.source.read_main_list()
        self.cache = apt_pkg.Cache()
        try:
            self.cache.update(self, self.source)
        except BaseException as e:
            print(e)
            pass

        apt_pkg.config.set("APT::Default-Release", suite)

        self.cache = apt_pkg.Cache()
        try:
            self.cache.update(self, self.source)
        except BaseException as e:
            print(e)
            pass

    def __del__(self):
        os.system('rm -rf "%s"' % self.projectpath)

    def start(self):
        pass

    def stop(self):
        pass

    def pulse(self, _obj):
        return True

    def mkdir_p(self, newdir, mode=0o755):
        """works the way a good mkdir -p would...
                - already exists, silently complete
                - regular file in the way, raise an exception
                - parent directory(ies) does not exist, make them as well
        """
        if os.path.isdir(newdir):
            pass
        elif os.path.isfile(newdir):
            raise OSError("a file with the same name as the desired "
                          "dir, '%s', already exists." % newdir)
        else:
            os.makedirs(newdir, mode)
            """ mode is not set correctly """
            os.system("chmod 777 " + newdir)

    def touch(self, file):
        if os.path.exists(file):
            os.utime(file, None)
        else:
            file = open(file, "w")
            file.close()

    def initialize_dirs(self):
        self.mkdir_p(os.path.join(self.projectpath, "cache/archives/partial"))
        self.mkdir_p(os.path.join(self.projectpath, "etc/apt/preferences.d"))
        self.mkdir_p(os.path.join(self.projectpath, "etc/apt/trusted.gpg.d"))
        self.mkdir_p(os.path.join(self.projectpath, "db"))
        self.mkdir_p(os.path.join(self.projectpath, "log"))
        self.mkdir_p(os.path.join(self.projectpath, "state/lists/partial"))
        self.touch(os.path.join(self.projectpath, "state/status"))

    def setup_gpg(self):
        ring_path = os.path.join(self.projectpath, "etc/apt/trusted.gpg")
        if not os.path.isdir("/etc/apt/trusted.gpg.d"):
            print("/etc/apt/trusted.gpg.d doesn't exist")
            print("apt-get install debian-archive-keyring may "
                  "fix this problem")
            sys.exit(20)

        if os.path.exists("/etc/apt/trusted.gpg"):
            system('cp /etc/apt/trusted.gpg "%s"' % ring_path)

        gpg_options = '--keyring "%s" --no-auto-check-trustdb ' \
                      '--trust-model always --no-default-keyring ' \
                      '--homedir "%s"' % (ring_path, self.projectpath)

        system('gpg %s --import "%s"' % (
            gpg_options,
            elbe_pubkey_fname))

        trustkeys = os.listdir("/etc/apt/trusted.gpg.d")
        for key in trustkeys:
            print("Import %s: " % key)
            try:
                system('gpg %s --import "%s"' % (
                    gpg_options,
                    os.path.join("/etc/apt/trusted.gpg.d", key)))
            except CommandError:
                print("adding elbe-pubkey to keyring failed")

    def add_pubkey_url(self, url):
        ring_path = os.path.join(self.projectpath, "etc/apt/trusted.gpg")
        tmpkey_path = os.path.join(self.projectpath, "tmpkey.gpg")

        gpg_options = '--keyring "%s" --no-auto-check-trustdb ' \
                      '--trust-model always --no-default-keyring ' \
                      '--homedir "%s"' % (ring_path, self.projectpath)

        try:
            system('wget -O "%s" "%s"' % (tmpkey_path, url))
            system('gpg %s --import "%s"' % (
                gpg_options,
                tmpkey_path))
        finally:
            system('rm "%s"' % tmpkey_path, allow_fail=True)

    def create_apt_sources_list(self, mirror):
        filename = os.path.join(self.projectpath, "etc/apt/sources.list")

        if os.path.exists(filename):
            os.remove(filename)

        file = open(filename, "w")
        file.write(mirror)
        file.close()

    def create_apt_prefs(self, prefs):
        filename = os.path.join(self.projectpath, "etc/apt/preferences")

        if os.path.exists(filename):
            os.remove(filename)

        file = open(filename, "w")
        file.write(prefs)
        file.close()

    def get_uri(self, suite, arch, target_pkg, incl_deps=False):

        d = apt_pkg.DepCache(self.cache)

        if not incl_deps:
            return [lookup_uri(self, d, target_pkg)]

        deps = [lookup_uri(self, d, target_pkg)]
        togo = [target_pkg]
        while len(togo):
            pp = togo.pop()
            try:
                pkg= self.cache[pp]
                c = d.get_candidate_ver(pkg)
            except KeyError:
                pkg = None
                c = None
            if not c:
                for p in self.cache.packages:
                    for x in p.provides_list:
                        if pp == x[0]:
                            pkg = self.cache[x[2].parent_pkg.name]
                            c = d.get_candidate_ver(pkg)
            if not c:
                print("couldnt get candidate: %s" % pkg)
            else:
                for p in getdeps(c):
                    if len([y for y in deps if y[0] == p]):
                        continue
                    if p != target_pkg and p == pp:
                        continue
                    deps.append(lookup_uri(self, d, p))
                    togo.append(p)

        return deps

class MyMan(BaseManager):
    pass

MyMan.register("VirtRPCAPTCache", VirtApt)

def get_virtaptcache(arch, suite, sources, prefs, keylist=[]):
    mm = MyMan()
    mm.start()

    # Disable false positive, because pylint can not
    # see the creation of MyMan.VirtRPCAPTCache by
    # MyMan.register()
    #
    # pylint: disable=no-member
    return mm.VirtRPCAPTCache(arch, suite, sources, prefs, keylist)
