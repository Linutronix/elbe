# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2014-2017 Linutronix GmbH
# SPDX-FileCopyrightText: 2015 Ferdinand Schwenk <ferdinand.schwenk@emtrion.de>

import functools
import os
import re
import socket
from urllib.error import URLError
from urllib.request import (
    HTTPBasicAuthHandler,
    HTTPPasswordMgrWithDefaultRealm,
    build_opener,
    install_opener,
    urlopen,
)

from elbepack.treeutils import etree
from elbepack.validate import validate_xml
from elbepack.version import elbe_version
from elbepack.xmldefaults import ElbeDefaults


class ValidationError(Exception):
    def __init__(self, validation):
        super().__init__()
        self.validation = validation

    def __repr__(self):
        rep = 'Elbe XML Validation Error\n'
        for v in self.validation:
            rep += (v + '\n')
        return rep

    def __str__(self):
        retval = ''
        for v in self.validation:
            retval += (v + '\n')
        return retval


class NoInitvmNode(Exception):
    pass


class ValidationMode:
    NO_CHECK = 1
    CHECK_BINARIES = 2
    CHECK_ALL = 0


def replace_localmachine(mirror, initvm=True):
    if initvm:
        localmachine = '10.0.2.2'
    else:
        localmachine = 'localhost'

    return mirror.replace('LOCALMACHINE', localmachine)


class ElbeXML:

    def __init__(
            self,
            fname,
            buildtype=None,
            skip_validate=False,
            url_validation=ValidationMode.NO_CHECK):
        if not skip_validate:
            validation = validate_xml(fname)
            if validation:
                raise ValidationError(validation)

        self.xml = etree(fname)

        if buildtype:
            pass
        elif self.xml.has('project/buildtype'):
            buildtype = self.xml.text('/project/buildtype')
        else:
            buildtype = 'nodefaults'
        self.defs = ElbeDefaults(buildtype)

        if not skip_validate and url_validation != ValidationMode.NO_CHECK:
            self.validate_apt_sources(url_validation, self.defs['arch'])

    def __getstate__(self):
        state = self.__dict__.copy()
        state['xml'] = state['xml'].tostring()
        state.pop('prj', None)
        state.pop('tgt', None)
        return state

    def __setstate__(self, state):
        state['xml'] = etree(None, string=state['xml'])
        self.__dict__.update(state)

    def text(self, txt, key=None):
        if key:
            return self.xml.text(txt, default=self.defs, key=key)
        return self.xml.text(txt)

    def has(self, path):
        return self.xml.has(path)

    def node(self, path):
        return self.xml.node(path)

    def all(self, path):
        return self.xml.all(path)

    @functools.cached_property
    def prj(self):
        return self.xml.node('/project')

    @functools.cached_property
    def tgt(self):
        return self.xml.node('/target')

    def is_cross(self, host_arch):

        target = self.text('project/buildimage/arch', key='arch')

        if host_arch == target:
            return False

        if (host_arch == 'amd64') and (target == 'i386'):
            return False

        if (host_arch == 'armhf') and (target == 'armel'):
            return False

        return True

    def get_initvm_primary_mirror(self, cdrompath):
        if self.xml.has('initvm/mirror/primary_host'):
            m = self.node('initvm/mirror')

            mirror = m.text('primary_proto') + '://'
            mirror += f"{m.text('primary_host')}/{m.text('primary_path')}".replace('//', '/')

        elif self.xml.has('initvm/mirror/cdrom') and cdrompath:
            mirror = f'file://{cdrompath}'

        return mirror.replace('LOCALMACHINE', '10.0.2.2')

    def get_primary_mirror(self, cdrompath, initvm=True, hostsysroot=False):
        if self.prj.has('mirror/primary_host'):
            m = self.prj.node('mirror')

            if hostsysroot and self.prj.has('mirror/host'):
                mirror = m.text('host')
            else:
                mirror = m.text('primary_proto') + '://'
                mirror += f"{m.text('primary_host')}/{m.text('primary_path')}".replace('//', '/')

        elif self.prj.has('mirror/cdrom') and cdrompath:
            mirror = f'file://{cdrompath}'

        return replace_localmachine(mirror, initvm)

    def get_primary_key(self, cdrompath, hostsysroot=False):
        if self.prj.has('mirror/cdrom') and cdrompath:
            return

        if self.prj.has('mirror/primary_host'):
            mirror = self.prj.node('mirror')

            if hostsysroot and mirror.has('host') and mirror.has('mirror/host_key'):
                return mirror.text('host_key')

            if mirror.has('primary_key'):
                return mirror.text('primary_key')

    # XXX: maybe add cdrom path param ?
    def create_apt_sources_list(self, build_sources=False, initvm=True, hostsysroot=False):

        if self.prj is None:
            return '# No Project'

        if not self.prj.has('mirror') and not self.prj.has('mirror/cdrom'):
            return '# no mirrors configured'

        goptions = []
        mirrors = []
        suite = self.prj.text('suite')

        if self.prj.has('mirror/primary_host'):

            pmirror = self.get_primary_mirror(None, hostsysroot=hostsysroot)

            if self.prj.has('mirror/options'):
                poptions = [opt.et.text.strip(' \t\n')
                            for opt
                            in self.prj.all('mirror/options/option')]
            else:
                poptions = []

            if hostsysroot:
                arch = self.text('project/buildimage/sdkarch', key='sdkarch')
            else:
                arch = self.text('project/buildimage/arch', key='arch')

            poptions = goptions + poptions

            if build_sources or self.tgt.has('pbuilder/src-pkg'):
                mirrors.append(
                    f"deb-src [{' '.join(poptions)}] {pmirror} {suite} main")

            poptions.append(f'arch={arch}')

            mirrors.append(f"deb [{' '.join(poptions)}] {pmirror} {suite} main")

            if self.prj.has('mirror/url-list'):

                for url in self.prj.node('mirror/url-list'):

                    if url.has('options'):
                        options = [opt.et.text.strip(' \t\n')
                                   for opt
                                   in url.all('options/option')]
                    else:
                        options = []

                    options = goptions + options

                    if url.has('binary'):
                        bin_url = url.text('binary').strip()
                        mirrors.append(f"deb [{' '.join(options)}] {bin_url}")

                    if url.has('source'):
                        src_url = url.text('source').strip()
                        mirrors.append(
                            f"deb-src [{' '.join(options)}] {src_url}")

        if self.prj.has('mirror/cdrom'):
            mirrors.append(f'deb copy:///cdrom/targetrepo {suite} main added')

        return replace_localmachine('\n'.join(mirrors), initvm)

    @staticmethod
    def validate_repo(r):
        try:
            fp = urlopen(r['url'] + 'InRelease', None, 30)
        except URLError:
            try:
                fp = urlopen(r['url'] + 'Release', None, 30)
            except URLError:
                return False
            except socket.timeout:
                return False
        except socket.timeout:
            return False

        ret = False
        if 'srcstr' in r:
            for line in fp:
                needle = r['srcstr'].encode(encoding='utf-8')
                if line.find(needle) != -1:
                    ret = True
                    break
        elif 'binstr' in r:
            for line in fp:
                needle = r['binstr'].encode(encoding='utf-8')
                if line.find(needle) != -1:
                    ret = True
                    break
        else:
            # This should never happen, either bin or src
            ret = False

        fp.close()
        return ret

    def validate_apt_sources(self, url_validation, arch):

        slist = self.create_apt_sources_list()
        sources_lines = slist.split('\n')

        repos = []
        for line in sources_lines:
            line = re.sub(r'\[.*\] ', '', line)
            if line.startswith('deb copy:'):
                # This is a cdrom, we dont verify it
                pass
            elif line.startswith('deb-src copy:'):
                # This is a cdrom, we dont verify it
                pass
            elif line.startswith('deb ') or line.startswith('deb-src '):
                # first check the validation mode, and
                # only add the repo, when it matches
                # the valudation mode
                if url_validation == ValidationMode.NO_CHECK:
                    continue

                if line.startswith('deb-src ') and \
                   url_validation != ValidationMode.CHECK_ALL:
                    continue

                lsplit = line.split(' ')
                url = lsplit[1]
                suite = lsplit[2]
                r = {}

                #
                # NOTE: special interpretation if suite followed by slash
                #
                # deb http://mirror foo  --> URI-Prefix: http://mirror/dist/foo
                # deb http://mirror foo/ --> URI-Prefix: http://mirror/foo
                #
                if suite.endswith('/'):
                    r['url'] = f'{url}/{suite}'
                else:
                    r['url'] = f'{url}/dists/{suite}/'

                #
                # Try to get sections.
                # If no sections has been passed, this is also valid syntax but
                # needs some special handling.
                #
                try:
                    section = lsplit[3]
                    if line.startswith('deb '):
                        r['binstr'] = (f'{section}/binary-{arch}/Packages')
                    else:
                        r['srcstr'] = (f'{section}/source/Sources')
                except IndexError:
                    if line.startswith('deb '):
                        r['binstr'] = 'Packages'
                    else:
                        r['srcstr'] = 'Sources'

                repos.append(r)

        if not self.prj:
            return

        if self.prj.has('mirror/primary_proxy'):
            os.environ['no_proxy'] = '10.0.2.2,localhost,127.0.0.1'
            proxy = self.prj.text(
                'mirror/primary_proxy').strip().replace('LOCALMACHINE',
                                                        '10.0.2.2')
            os.environ['http_proxy'] = proxy
            os.environ['https_proxy'] = proxy
        else:
            os.environ['http_proxy'] = ''
            os.environ['https_proxy'] = ''
            os.environ['no_proxy'] = ''

        passman = HTTPPasswordMgrWithDefaultRealm()
        authhandler = HTTPBasicAuthHandler(passman)
        opener = build_opener(authhandler)
        install_opener(opener)

        for r in repos:
            if '@' in r['url']:
                t = r['url'].split('@')
                if '://' in t[0]:
                    scheme, auth = t[0].split('://')
                    scheme = scheme + '://'
                else:
                    scheme = ''
                    auth = t[0]
                r['url'] = scheme + t[1]
                usr, passwd = auth.split(':')
                passman.add_password(None, r['url'], usr, passwd)
            if not self.validate_repo(r):
                if 'srcstr' in r:
                    raise ValidationError(
                        [f"Repository {r['url']}, {r['srcstr']} can not be validated"])
                if 'binstr' in r:
                    raise ValidationError(
                        [f"Repository {r['url']}, {r['binstr']} can not be validated"])
                raise ValidationError(
                    [f"Repository {r['url']} can not be validated"])

    def get_target_packages(self):
        if not self.xml.has('/target/pkg-list'):
            return []
        return [p.et.text for p in self.xml.node('/target/pkg-list')]

    def add_target_package(self, pkg):
        plist = self.xml.ensure_child('/target/pkg-list')

        # only add package once
        for p in plist:
            if p.et.text == pkg:
                return

        pak = plist.append('pkg')
        pak.set_text(pkg)
        pak.et.tail = '\n'

    def set_target_packages(self, pkglist):
        plist = self.xml.ensure_child('/target/pkg-list')
        plist.clear()
        for p in pkglist:
            pak = plist.append('pkg')
            pak.set_text(p)
            pak.et.tail = '\n'

    def get_buildenv_packages(self):
        retval = []
        if self.prj.has('buildimage/pkg-list'):
            retval = [p.et.text for p in self.prj.node('buildimage/pkg-list')]

        return retval

    def clear_pkglist(self, name):
        tree = self.xml.ensure_child(name)
        tree.clear()

    def append_pkg(self, aptpkg, name):
        tree = self.xml.ensure_child(name)
        pak = tree.append('pkg')
        pak.set_text(aptpkg.name)
        pak.et.tail = '\n'
        if aptpkg.installed_version is not None:
            pak.et.set('version', aptpkg.installed_version)
            pak.et.set('prio', aptpkg.installed_prio)
            pak.et.set('arch', aptpkg.installed_arch)
            hashes = aptpkg.installed_hashes
        else:
            pak.et.set('version', aptpkg.candidate_version)
            pak.et.set('prio', aptpkg.candidate_prio)
            pak.et.set('arch', aptpkg.candidate_arch)
            hashes = aptpkg.candidate_hashes

        for k, v in hashes.items():
            pak.et.set(k, v)

        pak.et.set('release-origin', aptpkg.origin.origin)
        pak.et.set('release-name', aptpkg.origin.codename)
        pak.et.set('uri', aptpkg.origin.uri)

        if aptpkg.is_auto_installed:
            pak.et.set('auto', 'true')
        else:
            pak.et.set('auto', 'false')

    def clear_full_pkglist(self):
        tree = self.xml.ensure_child('fullpkgs')
        tree.clear()

    def clear_debootstrap_pkglist(self):
        tree = self.xml.ensure_child('debootstrappkgs')
        tree.clear()

    def clear_initvm_pkglist(self):
        tree = self.xml.ensure_child('initvmpkgs')
        tree.clear()

    def append_full_pkg(self, aptpkg):
        self.append_pkg(aptpkg, 'fullpkgs')

    def append_debootstrap_pkg(self, aptpkg):
        self.append_pkg(aptpkg, 'debootstrappkgs')

    def append_initvm_pkg(self, aptpkg):
        self.append_pkg(aptpkg, 'initvmpkgs')

    def get_debootstrappkgs_from(self, other):
        tree = self.xml.ensure_child('debootstrappkgs')
        tree.clear()

        if not other.has('debootstrappkgs'):
            return

        for e in other.node('debootstrappkgs'):
            tree.append_treecopy(e)

    def get_initvmnode_from(self, other):
        ivm = other.node('initvm')
        if ivm is None:
            raise NoInitvmNode()

        tree = self.xml.ensure_child('initvm')
        tree.clear()

        for e in ivm:
            tree.append_treecopy(e)

        self.xml.set_child_position(tree, 0)

    def get_initvm_codename(self):
        if self.has('initvm/suite'):
            return self.text('initvm/suite')
        return None

    def set_cdrom_mirror(self, abspath):
        mirror = self.node('project/mirror')
        mirror.clear()
        cdrom = mirror.ensure_child('cdrom')
        cdrom.set_text(abspath)

    def dump_elbe_version(self):
        version = self.xml.ensure_child('elbe_version')
        version.set_text(elbe_version)

    def get_elbe_version(self):
        if self.has('elbe_version'):
            return self.text('elbe_version')
        return 'no version'
