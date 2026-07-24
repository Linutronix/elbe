# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2024 Linutronix GmbH

import argparse
import contextlib
import datetime
import itertools
import json
import os
import sys
import urllib.parse

from elbepack.aptpkgutils import XMLPackage
from elbepack.commands.parselicence import LicenseType, extract_licenses_from_report
from elbepack.elbexml import ElbeXML
from elbepack.uuid7 import uuid7
from elbepack.version import elbe_version


class CycloneDXEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime.datetime):
            if obj.tzinfo is not datetime.timezone.utc:
                raise ValueError('only UTC datetimes are supported')
            return obj.isoformat()


def _licence_from_pkg(pkg, licenses):
    if pkg.name in licenses:
        lics = []
        for lic in licenses[pkg.name][0]:
            if lic is None:
                pass
            elif lic.type == LicenseType.UNKNOWN:
                lics.append({'license': {'name': lic.name,
                                         'text': {'content': lic.text}}})
            elif lic.type == LicenseType.SPDX:
                lics.append({'license': {'id': lic.name}})
            elif lic.type == LicenseType.SPDX_EXCEPTION:
                lics.append({'license': {'name': lic.name}})
            else:
                raise ValueError(lic.type)
        return lics


def _remove_empty_fields(dict):
    return {k: v for k, v in dict.items() if v is not None}


def _repository_url(uri):
    parsed = urllib.parse.urlsplit(uri)
    path_parts = parsed.path.split('/')

    if path_parts[-1].endswith('.deb'):
        # Standard Debian layout: repository root is everything before /pool/.
        if 'pool' in path_parts:
            repo_path = '/'.join(path_parts[:path_parts.index('pool')])
        else:
            # Flat repository: repo URL is everything before the filename.
            repo_path = '/'.join(path_parts[:-1])

        if not repo_path:
            repo_path = '/'

        return urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, repo_path, '', ''))

    raise ValueError(f'Unexpected URI format: {uri}')


def _purl_from_pkg(pkg):
    purl_qualifiers = urllib.parse.urlencode({
                          'arch': pkg.installed_arch,
                          'distro': pkg.origin.codename,
                          'repository_url': _repository_url(pkg.origin.uri),
                      })
    return urllib.parse.urlunparse(
               urllib.parse.ParseResult(
                   scheme='pkg',
                   netloc='',
                   path=f'deb/{pkg.origin.origin.lower()}/{pkg.name}@{pkg.installed_version}',
                   params='',
                   query=purl_qualifiers,
                   fragment='',
               )
           )


def _component_from_apt_pkg(pkg, licenses):
    hash_name_mapping = {
            'md5': 'MD5',
            'sha1': 'SHA-1',
            'sha256': 'SHA-256',
            'sha512': 'SHA-512',
    }
    hashes = []
    for key in pkg.installed_hashes:
        alg = hash_name_mapping.get(key)
        content = pkg.installed_hashes[key]
        hashes.append({'alg': alg, 'content': content})

    if pkg.name.startswith('lib'):
        type = 'library'
    else:
        type = 'application'

    return _remove_empty_fields({
        'type': type,
        'name': pkg.name,
        'version': pkg.installed_version,
        'hashes': hashes,
        'licenses': _licence_from_pkg(pkg, licenses),
        'purl': _purl_from_pkg(pkg),
    })


class _FileStream:
    def __init__(self, mode, default):
        self.mode = mode
        self.default = default

    def __call__(self, path):
        self.path = path
        return self

    def open(self):
        if self.path == '-':
            return contextlib.nullcontext(self.default)
        return open(self.path, self.mode)


def run_command(argv):
    aparser = argparse.ArgumentParser(prog='elbe cyclonedx-sbom')
    aparser.add_argument('-o', '--output', type=_FileStream('w', sys.stdout), default='-')
    aparser.add_argument('-e', '--errors', type=_FileStream('w', sys.stderr), default='-')
    aparser.add_argument('-d', dest='elbe_build', required=True)
    aparser.add_argument('-m', dest='mapping', nargs='?', default=None)
    args = aparser.parse_args(argv)

    ts = datetime.datetime.now(tz=datetime.timezone.utc)
    project_dir = args.elbe_build
    source_file = ElbeXML(os.path.join(project_dir, 'source.xml'))

    project_name = source_file.text('/name').strip()
    project_version = source_file.text('/version').strip()
    project_description = source_file.text('/description').strip()
    licenses = extract_licenses_from_report(
                   os.path.join(project_dir, 'licence-target.xml'), args.mapping)
    chroot_lics = extract_licenses_from_report(
                   os.path.join(project_dir, 'licence-chroot.xml'), args.mapping)

    pkg_list = []
    for p in source_file.node('fullpkgs'):
        pkg = XMLPackage(p)
        pkg_list.append(pkg)

    components = []
    for pkg in pkg_list:
        components.append(_component_from_apt_pkg(pkg, licenses))

    formulation_components = []
    for p in itertools.chain(
        source_file.node('debootstrappkgs') or [],
        source_file.node('initvmpkgs') or [],
    ):
        # Duplicates are disallowed by the schema
        c = _component_from_apt_pkg(XMLPackage(p), chroot_lics)
        if c not in formulation_components:
            formulation_components.append(c)

    output = {
        'bomFormat': 'CycloneDX',
        'specVersion': '1.6',
        'serialNumber': uuid7(ts).urn,
        'version': 1,
        'metadata': {
          'timestamp': ts,
          'tools': [
            {
              'vendor': 'Linutronix',
              'name': 'Elbe',
              'version': elbe_version,
            },
          ],
          'component': {
            'type': 'operating-system',
            'name': project_name,
            'version': project_version,
            'description': project_description,
          },
        },
        'components': components,
        'formulation': [
          {
            'components': formulation_components,
          },
        ],
    }

    with args.output.open() as out:
        json.dump(output, out, indent=2, cls=CycloneDXEncoder)
        out.write('\n')

    def _print_error_report(dest, pkg_errors):
        if pkg_errors is not None:
            print(f'{pkg.name}', file=errors)
            for error in pkg_errors:
                print(f'  {error}', file=errors)
            print('', file=errors)

    def _errors_from_pkg(pkg, licenses):
        if pkg.name in licenses:
            if licenses[pkg.name][1]:
                return licenses[pkg.name][1]

    with args.errors.open() as errors:
        errors.write('\nThe following target-packages have errors:\n\n')
        for pkg in pkg_list:
            _print_error_report(errors, _errors_from_pkg(pkg, licenses))

        errors.write('\nThe following chroot-packages have errors:\n\n')
        for pkg in pkg_list:
            _print_error_report(errors, _errors_from_pkg(pkg, chroot_lics))
