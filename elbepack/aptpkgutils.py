# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2005-2009 Canonical
# SPDX-FileCopyrightText: 2014, 2017 Linutronix GmbH

import dataclasses
import os

MARKED_INSTALL = 0
MARKED_UPGRADE = 1
MARKED_DELETE = 2
UPGRADABLE = 3
INSTALLED = 4
NOTINSTALLED = 5

statestring = {
    MARKED_INSTALL: 'MARKED_INSTALL',
    MARKED_UPGRADE: 'MARKED_UPGRADE',
    MARKED_DELETE: 'MARKED_DELETE',
    UPGRADABLE: 'UPGRADABLE',
    INSTALLED: 'INSTALLED',
    NOTINSTALLED: 'NOT INSTALLED'
}


# Mapping from apt_pkg.HashString to elbe xml
_apt_hash_mapping = {
    'MD5Sum': 'md5',
    'SHA1': 'sha1',
    'SHA256': 'sha256',
    'SHA512': 'sha512',
}


@dataclasses.dataclass
class Origin:
    origin: str
    codename: str
    site: str
    component: str
    uri: str


@dataclasses.dataclass
class Source:
    name: str
    version: str


def _apt_pkg_hashes(pkg):
    r = {}

    for h in pkg._records.hashes:
        t = _apt_hash_mapping.get(h.hashtype)
        if t is None:
            continue

        assert t not in r
        r[t] = h.hashvalue

    return r


def getdeps(pkg):
    for dd in pkg.dependencies:
        for d in dd:
            yield d.name


def getalldeps(c, pkgname, blacklist=()):
    retval = [pkgname]
    togo = [pkgname]

    while togo:
        pp = togo.pop()
        if pp in blacklist:
            continue
        pkg = c[pp]

        for p in getdeps(pkg.candidate):
            if p in retval:
                continue
            if p in blacklist:
                continue
            if p not in c:
                continue
            retval.append(p)
            togo.append(p)

    return retval


def pkgstate(pkg):
    if pkg.marked_install:
        return MARKED_INSTALL
    if pkg.marked_upgrade:
        return MARKED_UPGRADE
    if pkg.marked_delete:
        return MARKED_DELETE
    if pkg.is_upgradable:
        return UPGRADABLE
    if pkg.is_installed:
        return INSTALLED
    return NOTINSTALLED


def pkgorigin(pkg):
    if pkg.installed:
        o = pkg.installed.origins[0]
        origin = Origin(origin=o.origin, codename=o.codename,
                        site=o.site, component=o.component, uri=pkg.installed.uri)
    else:
        origin = None

    return origin


def pkgsource(pkg):
    if pkg.installed:
        i = pkg.installed
        source = Source(name=i.source_name, version=i.source_version)
    else:
        source = None

    return source


def fetch_source(name, version, destdir, progress=None):
    import apt
    import apt_pkg

    allow_untrusted = apt_pkg.config.find_b('APT::Get::AllowUnauthenticated', False)

    rec = apt_pkg.SourceRecords()
    acq = apt_pkg.Acquire(progress or apt.progress.text.AcquireProgress())

    # poorman's iterator
    while True:
        next_p = rec.lookup(name)
        # End of the list?
        if not next_p:
            raise ValueError(
                f'No source found for {name}_{version}')
        if version == rec.version:
            break

    # We don't allow untrusted package and the package is not
    # marks as trusted
    if not (allow_untrusted or rec.index.is_trusted):
        raise apt.package.FetchError(
            f"Can't fetch source {name}_{version}; "
            f'Source {rec.index.describe} is not trusted')

    # Copy from src to dst all files of the source package
    dsc = None
    files = []
    for _file in rec.files:
        src = os.path.basename(_file.path)
        dst = os.path.join(destdir, src)

        if 'dsc' == _file.type:
            dsc = dst

        if not (allow_untrusted or _file.hashes.usable):
            raise apt.package.FetchError(
                f"Can't fetch file {dst}. No trusted hash found.")

        # acq is accumlating the AcquireFile, the files list only
        # exists to prevent Python from GC the object .. I guess.
        # Anyway, if we don't keep the list, We will get an empty
        # directory
        files.append(apt_pkg.AcquireFile(acq, rec.index.archive_uri(_file.path),
                                         _file.hashes, _file.size, src, destfile=dst))
    acq.run()

    if dsc is None:
        raise ValueError(f'No source found for {name}_{version}')

    for item in acq.items:
        if item.STAT_DONE != item.status:
            raise apt.package.FetchError(
                f"Can't fetch item {item.destfile}: {item.error_text}")

    return os.path.abspath(dsc)


def parse_built_using(value):
    """
    >>> list(parse_built_using(None))
    []

    >>> list(parse_built_using('grub2 (= 1.99-9), loadlin (= 1.6e-1)'))
    [('grub2', '1.99-9'), ('loadlin', '1.6e-1')]
    """
    import apt_pkg

    if value is None:
        return

    for group in apt_pkg.parse_src_depends(value):
        assert len(group) == 1

        package, version, operation = group[0]
        assert operation == '='

        yield package, version


def get_corresponding_source_packages(cache, pkg_lst=None, include_built_using=True):

    if pkg_lst is None:
        pkg_lst = {p.name for p in cache if p.is_installed}

    src_set = set()

    for pkg in pkg_lst:
        if isinstance(pkg, str):
            version = cache[pkg].installed or cache[pkg.candidate]
        elif isinstance(pkg, PackageBase):
            version = cache[pkg.name].versions[pkg.installed_version]

        src_set.add((version.source_name, version.source_version))

        if include_built_using:
            for name, ver in parse_built_using(version.record.get('Built-Using')):
                src_set.add((name, ver))

    return list(src_set)


class PackageBase:

    def __init__(self, name,
                 installed_version, candidate_version,
                 installed_hashes, candidate_hashes,
                 installed_prio, candidate_prio,
                 installed_arch, candidate_arch,
                 state, is_auto_installed, origin, source):

        self.name = name
        self.installed_version = installed_version
        self.candidate_version = candidate_version
        self.installed_hashes = installed_hashes
        self.candidate_hashes = candidate_hashes
        self.installed_prio = installed_prio
        self.candidate_prio = candidate_prio
        self.installed_arch = installed_arch
        self.candidate_arch = candidate_arch
        self.state = state
        self.is_auto_installed = is_auto_installed
        self.origin = origin
        self.source = source

    def __repr__(self):
        return (f'<{type(self).__name__} {self.name}-{self.installed_version} state: '
                f'{statestring[self.state]}>')

    def __eq__(self, other):
        vereq = (self.installed_version == other.installed_version)
        nameq = (self.name == other.name)

        return vereq and nameq


class APTPackage(PackageBase):
    def __init__(self, pkg):
        iver = pkg.installed and pkg.installed.version
        cver = pkg.candidate and pkg.candidate.version
        ihashes = pkg.installed and _apt_pkg_hashes(pkg.installed)
        chashes = pkg.candidate and _apt_pkg_hashes(pkg.candidate)
        iprio = pkg.installed and pkg.installed.priority
        cprio = pkg.candidate and pkg.candidate.priority
        iarch = pkg.installed and pkg.installed.architecture
        carch = pkg.candidate and pkg.candidate.architecture

        if pkg.installed:
            self.installed_deb = os.path.basename(pkg.installed.filename)
        else:
            self.installed_deb = None

        super().__init__(pkg.name,
                         iver, cver,
                         ihashes, chashes,
                         iprio, cprio,
                         iarch, carch,
                         pkgstate(pkg),
                         pkg.is_auto_installed,
                         pkgorigin(pkg),
                         pkgsource(pkg))


class XMLPackage(PackageBase):
    def __init__(self, node):
        hashes = {}
        for h in _apt_hash_mapping.values():
            v = node.et.get(h)
            if v is not None:
                hashes[h] = v

        origin = Origin(origin=node.et.get('release-origin'),
                        codename=node.et.get('release-name'),
                        uri=node.et.get('uri'),
                        site=None,
                        component=None)

        source_name = node.et.get('source-name')
        source_version = node.et.get('source-version')

        if source_name is not None and source_version is not None:
            source = Source(name=source_name, version=source_version)
        else:
            source = None

        super().__init__(node.et.text,
                         node.et.get('version'), None,
                         hashes, None,
                         node.et.get('prio'), None,
                         node.et.get('arch'), None,
                         INSTALLED, node.et.get('auto') == 'true',
                         origin, source)
