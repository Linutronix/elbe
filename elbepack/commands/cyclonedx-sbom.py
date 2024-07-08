# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2024 Linutronix GmbH

import datetime
import itertools
import json
import optparse
import os
import sys
import urllib

from elbepack.aptpkgutils import XMLPackage
from elbepack.elbexml import ElbeXML
from elbepack.uuid7 import uuid7
from elbepack.version import elbe_version


class CycloneDXEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime.datetime):
            if obj.tzinfo is not datetime.timezone.utc:
                raise ValueError('only UTC datetimes are supported')
            return obj.isoformat()


def _repository_url(uri):
    uri_parts = uri.split('/')
    if len(uri_parts) < 6:
        raise ValueError('URI needs to be in pool layout, and pool being the 5th or 6th segment')
    if uri_parts[-5] == 'pool':
        # http://deb.debian.org/debian/pool/main/a/adduser/adduser_3.134_all.deb
        return '/'.join(uri_parts[:-5])
    elif uri_parts[-6] == 'pool':
        # http://deb.debian.org/debian-security/pool/updates/main/u/util-linux/bsdutils_2.38.1-5%2bdeb12u1_amd64.deb
        return '/'.join(uri_parts[:-6])
    else:
        raise ValueError('URI needs to be in pool layout, and pool being the 5th or 6th segment')


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


def _component_from_apt_pkg(pkg):
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

    return {
        'type': type,
        'name': pkg.name,
        'version': pkg.installed_version,
        'hashes': hashes,
        'purl': _purl_from_pkg(pkg),
    }


def run_command(argv):
    oparser = optparse.OptionParser()
    oparser.add_option('-d', dest='elbe_build')
    options, args = oparser.parse_args(argv)

    if args != [] or options.elbe_build is None:
        print('invalid options')
        oparser.print_help()
        sys.exit(1)

    ts = datetime.datetime.now(tz=datetime.timezone.utc)
    project_dir = options.elbe_build
    source_file = ElbeXML(os.path.join(project_dir, 'source.xml'))

    project_name = source_file.text('/name').strip()
    project_version = source_file.text('/version').strip()
    project_description = source_file.text('/description').strip()

    pkg_list = []
    for p in source_file.node('fullpkgs'):
        pkg = XMLPackage(p)
        pkg_list.append(pkg)

    components = []
    for pkg in pkg_list:
        components.append(_component_from_apt_pkg(pkg))

    formulation_components = []
    for p in itertools.chain(
        source_file.node('debootstrappkgs'),
        source_file.node('initvmpkgs'),
    ):
        # Duplicates are disallowed by the schema
        if _component_from_apt_pkg(XMLPackage(p)) not in formulation_components:
            formulation_components.append(_component_from_apt_pkg(XMLPackage(p)))

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

    json.dump(output, sys.stdout, indent=2, cls=CycloneDXEncoder)
    sys.stdout.write('\n')
