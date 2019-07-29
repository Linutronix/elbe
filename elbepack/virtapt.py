# ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (c) 2013-2018 Manuel Traut <manut@linutronix.de>
# Copyright (c) 2014-2015, 2018 Torben Hohn <torben.hohn@linutronix.de>
# Copyright (c) 2018 John Ogness <john.ogness@linutronix.de>
# Copyright (c) 2018 Oliver Brandt <oliver.brandt@lenze.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import print_function

import os
import sys

from multiprocessing.managers import BaseManager

from elbepack.shellhelper import system

# don't remove the apt import, it is really needed, due to some magic in
# apt_pkg

import apt  # pylint: disable=unused-import
import apt_pkg


from elbepack.shellhelper import CommandError, system
from elbepack.filesystem import TmpdirFilesystem
from elbepack.xmldefaults import ElbeDefaults
from elbepack.rfs import create_apt_prefs


def getdeps(pkg):
    for dd in pkg.depends_list.get("Depends", []):
        for d in dd:
            yield d.target_pkg.name


# target_pkg is either a 'package name' or a 'provides'
#
# ATTENTION: for provides pinning and priorities for package selection are
#            ignored. This should be safe for now, because the code is only
#            used for generating the SDKs host-sysroot.
#            For generating host-sysroots there is no posibility to modify
#            package priorities via elbe-xml.
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


class VirtApt(object):
    def __init__(self, xml):

        self.xml = xml

        arch = xml.text("project/buildimage/arch", key="arch")
        suite = xml.text("project/suite")

        self.basefs = TmpdirFilesystem()
        self.initialize_dirs()

        create_apt_prefs(self.xml, self.basefs)

        mirror = self.xml.create_apt_sources_list(build_sources=True,
                                                  initvm=False)
        self.basefs.write_file("etc/apt/sources.list", 0o644, mirror)

        self.setup_gpg()
        self.import_keys()

        apt_pkg.config.set("APT::Architecture", arch)
        apt_pkg.config.set("APT::Architectures", arch)
        apt_pkg.config.set("Acquire::http::Proxy::127.0.0.1", "DIRECT")
        apt_pkg.config.set("APT::Install-Recommends", "0")
        apt_pkg.config.set("Dir::Etc", self.basefs.fname('/'))
        apt_pkg.config.set("Dir::Etc::Trusted",
                           self.basefs.fname('/etc/apt/trusted.gpg'))
        apt_pkg.config.set("Dir::Etc::TrustedParts",
                           self.basefs.fname('/etc/apt/trusted.gpg.d'))
        apt_pkg.config.set("APT::Cache-Limit", "0")
        apt_pkg.config.set("APT::Cache-Start", "32505856")
        apt_pkg.config.set("APT::Cache-Grow", "2097152")
        apt_pkg.config.set("Dir::State", self.basefs.fname("state"))
        apt_pkg.config.set("Dir::State::status",
                           self.basefs.fname("state/status"))
        apt_pkg.config.set("Dir::Cache", self.basefs.fname("cache"))
        apt_pkg.config.set("Dir::Cache::archives",
                           self.basefs.fname("cache/archives"))
        apt_pkg.config.set("Dir::Etc", self.basefs.fname("etc/apt"))
        apt_pkg.config.set("Dir::Log", self.basefs.fname("log"))
        if self.xml.has('project/noauth'):
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

        apt_pkg.config.set("APT::Default-Release", suite)

        self.cache = apt_pkg.Cache()
        try:
            self.cache.update(self, self.source)
        except BaseException as e:
            print(e)

        try:
            self.depcache = apt_pkg.DepCache(self.cache)
            prefs_name = self.basefs.fname("/etc/apt/preferences")
            self.depcache.read_pinfile(prefs_name)
        except BaseException as e:
            print(e)

        self.downloads = {}
        self.acquire = apt_pkg.Acquire(self)

    def add_key(self, key):
        cmd = 'echo "%s" > %s' % (key, self.basefs.fname("tmp/key.pub"))
        clean = 'rm -f %s' % self.basefs.fname("tmp/key.pub")
        system(cmd)
        system('fakeroot apt-key --keyring "%s" add "%s"' %
               (self.basefs.fname('/etc/apt/trusted.gpg'),
                self.basefs.fname("tmp/key.pub")))
        system(clean)

    def import_keys(self):
        if self.xml.has('project/mirror/url-list'):
            for url in self.xml.node('project/mirror/url-list'):
                if url.has('raw-key') and not url.bool_attr("noauth"):
                    key = "\n".join(line.strip(" \t") for line in url.text('raw-key').splitlines()[1:-1])
                    self.add_key(key)

    def start(self):
        pass

    def stop(self):
        pass

    def pulse(self, _obj):
        return True

    def initialize_dirs(self):
        self.basefs.mkdir_p("cache/archives/partial")
        self.basefs.mkdir_p("etc/apt/preferences.d")
        self.basefs.mkdir_p("etc/apt/trusted.gpg.d")
        self.basefs.mkdir_p("db")
        self.basefs.mkdir_p("log")
        self.basefs.mkdir_p("state/lists/partial")
        self.basefs.mkdir_p("tmp")
        self.basefs.touch_file("state/status")

    def setup_gpg(self):
        ring_path = self.basefs.fname("etc/apt/trusted.gpg")
        if not os.path.isdir("/etc/apt/trusted.gpg.d"):
            print("/etc/apt/trusted.gpg.d doesn't exist")
            print("apt-get install debian-archive-keyring may "
                  "fix this problem")
            sys.exit(20)

        if os.path.exists("/etc/apt/trusted.gpg"):
            system('cp /etc/apt/trusted.gpg "%s"' % ring_path)

        trustkeys = os.listdir("/etc/apt/trusted.gpg.d")
        for key in trustkeys:
            system('cp "/etc/apt/trusted.gpg.d/%s" "%s"' % (
                   key,
                   ring_path + '.d'))

    def mark_install(self, pkgname):
        self.depcache.mark_install(self.cache[pkgname])

    def marked_install(self, pkgname):
        return self.depcache.marked_install(self.cache[pkgname])

    def get_candidate_ver(self, pkgname):
        return self.depcache.get_candidate_ver(self.cache[pkgname]).ver_str

    def has_pkg(self, pkgname):
        return pkgname in self.cache

    def mark_pkg_download(self, pkgname):
        pkg = self.cache[pkgname]
        c = self.depcache.get_candidate_ver(pkg)

        r = apt_pkg.PackageRecords(self.cache)
        r.lookup(c.file_list[0])

        x = self.source.find_index(c.file_list[0][0])
        uri = x.archive_uri(r.filename)
        hashval = str(r.hashes.find('SHA256'))

        acq = apt_pkg.AcquireFile(self.acquire,
                                  uri,
                                  hash=hashval,
                                  size=c.size,
                                  descr=r.long_desc,
                                  short_descr=r.short_desc,
                                  destdir=self.basefs.fname('/cache/archives'))
        self.downloads[pkgname] = acq

    def do_downloads(self):
        res = self.acquire.run()
        print(res)

    def get_downloaded_files(self):
        ret = []
        for _, d in self.downloads.iteritems():
            if d.complete:
                ret.append(d.destfile)
            else:
                print('incomplete download "%s"' % d.desc_uri)

        return ret

    def get_downloaded_pkg(self, pkgname):
        d = self.downloads[pkgname]

        if not d.complete:
            print('incomplete download "%s"' % d.desc_uri)
            raise KeyError

        return d.destfile

    def get_uri(self, target_pkg, incl_deps=False):

        d = apt_pkg.DepCache(self.cache)

        if not incl_deps:
            return [lookup_uri(self, d, target_pkg)]

        deps = [lookup_uri(self, d, target_pkg)]
        togo = [target_pkg]
        while togo:
            pp = togo.pop()
            try:
                pkg = self.cache[pp]
                c = d.get_candidate_ver(pkg)
            except KeyError:
                pkg = None
                c = None
            if not c:
                # pylint: disable=E1133
                for p in self.cache.packages:
                    for x in p.provides_list:
                        if pp == x[0]:
                            pkg = self.cache[x[2].parent_pkg.name]
                            c = d.get_candidate_ver(pkg)
            if not c:
                print("couldnt get candidate: %s" % pkg)
            else:
                for p in getdeps(c):
                    if [y for y in deps if y[0] == p]:
                        continue
                    if p != target_pkg and p == pp:
                        continue
                    deps.append(lookup_uri(self, d, p))
                    togo.append(p)

        return list(set(deps))
