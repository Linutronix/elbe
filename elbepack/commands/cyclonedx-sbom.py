# ELBE - Debian Based Embedded Rootfilesystem Builder

import datetime
import json
import optparse
import os
import sys

from elbepack.aptpkgutils import XMLPackage
from elbepack.elbexml import ElbeXML
from elbepack.uuid7 import uuid7
from elbepack.version import elbe_version


class CycloneDXEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (datetime.date, datetime.datetime)):
            return obj.isoformat()


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
    }


def run_command(argv):
    oparser = optparse.OptionParser()
    oparser.add_option('-d', dest='elbe_build')
    options, args = oparser.parse_args()

    ts = datetime.datetime.now()
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
    }

    json.dump(output, sys.stdout, indent=2, cls=CycloneDXEncoder)
    sys.stdout.write('\n')
