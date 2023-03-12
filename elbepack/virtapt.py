# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2013-2018 Linutronix GmbH
# SPDX-FileCopyrightText: 2018 Oliver Brandt <oliver.brandt@lenze.com>

import os
import shutil
import sys

# don't remove the apt import, it is really needed, due to some magic in
# apt_pkg
import apt

import apt_pkg

from elbepack.egpg import unarmor_openpgp_keyring
from elbepack.filesystem import TmpdirFilesystem
from elbepack.rfs import create_apt_prefs
from elbepack.treeutils import strip_leading_whitespace_from_lines


class VirtApt:
    def __init__(self, xml):

        self.xml = xml

        arch = xml.text('project/buildimage/arch', key='arch')
        suite = xml.text('project/suite')

        self.basefs = TmpdirFilesystem()
        self._initialize_dirs()

        create_apt_prefs(self.xml, self.basefs)

        mirror = self.xml.create_apt_sources_list(build_sources=True,
                                                  initvm=False)
        self.basefs.write_file('etc/apt/sources.list', 0o644, mirror)

        self._setup_gpg()
        self._import_keys()

        apt_pkg.config.set('APT::Architecture', arch)
        apt_pkg.config.set('APT::Architectures', arch)
        apt_pkg.config.set('Acquire::http::Proxy::127.0.0.1', 'DIRECT')
        apt_pkg.config.set('APT::Install-Recommends', '0')
        apt_pkg.config.set('Dir::Etc', self.basefs.fname('/'))
        apt_pkg.config.set('Dir::Etc::Trusted',
                           self.basefs.fname('/etc/apt/trusted.gpg'))
        apt_pkg.config.set('Dir::Etc::TrustedParts',
                           self.basefs.fname('/etc/apt/trusted.gpg.d'))
        apt_pkg.config.set('APT::Cache-Limit', '0')
        apt_pkg.config.set('APT::Cache-Start', '32505856')
        apt_pkg.config.set('APT::Cache-Grow', '2097152')
        apt_pkg.config.set('Dir::State', self.basefs.fname('state'))
        apt_pkg.config.set('Dir::State::status',
                           self.basefs.fname('state/status'))
        apt_pkg.config.set('Dir::Cache', self.basefs.fname('cache'))
        apt_pkg.config.set('Dir::Cache::archives',
                           self.basefs.fname('cache/archives'))
        apt_pkg.config.set('Dir::Etc', self.basefs.fname('etc/apt'))
        apt_pkg.config.set('Dir::Log', self.basefs.fname('log'))
        if self.xml.has('project/noauth'):
            apt_pkg.config.set('APT::Get::AllowUnauthenticated', '1')
            apt_pkg.config.set('Acquire::AllowInsecureRepositories', '1')
        else:
            apt_pkg.config.set('APT::Get::AllowUnauthenticated', '0')
            apt_pkg.config.set('Acquire::AllowInsecureRepositories', '0')

        apt_pkg.init_system()

        progress = apt.progress.base.AcquireProgress()

        self.source = apt_pkg.SourceList()
        self.source.read_main_list()
        self.cache = apt_pkg.Cache()
        self.cache.update(progress, self.source)

        apt_pkg.config.set('APT::Default-Release', suite)

        self.cache = apt_pkg.Cache()
        self.cache.update(progress, self.source)

        self.depcache = apt_pkg.DepCache(self.cache)
        prefs_name = self.basefs.fname('/etc/apt/preferences')
        self.depcache.read_pinfile(prefs_name)

        self.downloads = {}
        self.acquire = apt_pkg.Acquire(progress)

    def _add_key(self, key, keyname):
        """
        Adds the binary OpenPGP keyring 'key' as a trusted apt keyring
        with file name 'keyname'.
        """
        with open(self.basefs.fname(f'/etc/apt/trusted.gpg.d/{keyname}'), 'wb') as outfile:
            outfile.write(key)

    def _import_keys(self):
        mirror = self.xml.node('project/mirror')
        if mirror and mirror.has('primary_host') and mirror.has('primary_key'):
            key = strip_leading_whitespace_from_lines(mirror.text('primary_key'))
            self.add_key(unarmor_openpgp_keyring(key), 'elbe-virtapt-primary-key.gpg')

        if self.xml.has('project/mirror/url-list'):
            # Should we use self.xml.prj.has("noauth")???
            #
            # If so, this is related to issue #220 -
            # https://github.com/Linutronix/elbe/issues/220
            #
            # I could make a none global 'noauth' flag for mirrors
            for i, url in enumerate(self.xml.node('project/mirror/url-list')):
                if url.has('raw-key'):
                    key = strip_leading_whitespace_from_lines(url.text('raw-key'))
                    self._add_key(unarmor_openpgp_keyring(key),
                                  f'elbe-virtapt-raw-key{i}.gpg')

    def _initialize_dirs(self):
        self.basefs.mkdir_p('cache/archives/partial')
        self.basefs.mkdir_p('etc/apt/preferences.d')
        self.basefs.mkdir_p('etc/apt/trusted.gpg.d')
        self.basefs.mkdir_p('db')
        self.basefs.mkdir_p('log')
        self.basefs.mkdir_p('state/lists/partial')
        self.basefs.mkdir_p('tmp')
        self.basefs.touch_file('state/status')

    def _setup_gpg(self):
        ring_path = self.basefs.fname('etc/apt/trusted.gpg')
        if not os.path.isdir('/etc/apt/trusted.gpg.d'):
            print("/etc/apt/trusted.gpg.d doesn't exist")
            print('apt-get install debian-archive-keyring may '
                  'fix this problem')
            sys.exit(204)

        if os.path.exists('/etc/apt/trusted.gpg'):
            shutil.copyfile('/etc/apt/trusted.gpg', ring_path)

        shutil.copytree('/etc/apt/trusted.gpg.d', ring_path + '.d', dirs_exist_ok=True)

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
        return self.acquire.run()

    def get_downloaded_pkg(self, pkgname):
        d = self.downloads[pkgname]

        if not d.complete:
            print(f'incomplete download "{d.desc_uri}"')
            raise KeyError

        return d.destfile

    def delete(self):
        self.basefs.delete()
