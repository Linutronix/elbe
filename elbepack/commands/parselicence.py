# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2016-2017 Linutronix GmbH

import argparse
import datetime
import io
import os
import subprocess
from tempfile import NamedTemporaryFile

from elbepack.treeutils import etree
from elbepack.version import elbe_version


class license_dep5_to_spdx (dict):
    def __init__(self, xml_fname=None):
        dict.__init__(self)

        self.perpackage_mapping = {}
        self.perpackage_override = {}
        if xml_fname is None:
            return

        xml = etree(xml_fname)

        if xml.root.has('global'):
            for mapping in xml.root.node('global'):
                self[mapping.et.attrib['name']] = mapping.et.text

        if xml.root.has('perpackage'):
            for pkg in xml.root.node('perpackage'):
                pname = pkg.et.attrib['name']
                self.perpackage_mapping[pname] = {}
                self.perpackage_override[pname] = []
                for pp in pkg:
                    if pp.tag == 'mapping':
                        self.perpackage_mapping[pname][pp.et.attrib['name']
                                                       ] = pp.et.text
                    if pp.tag == 'license':
                        self.perpackage_override[pname].append(pp.et.text)

    def have_override(self, pkgname):
        return pkgname in self.perpackage_override

    def get_override(self, pkgname):
        return self.perpackage_override[pkgname]

    def map_one_license(self, pkgname, lic):
        if pkgname in self.perpackage_mapping:
            if lic in self.perpackage_mapping[pkgname]:
                return self.perpackage_mapping[pkgname][lic]
        if lic in self:
            return self[lic]
        return None

    def map_one_license_with_exception(self, pkgname, lic, errors):
        with_split = lic.split(' with ')

        mapped_lic = self.map_one_license(pkgname, with_split[0])
        if mapped_lic is None:
            errors.append(f'no mapping for "{with_split[0]}" for pkg "{pkgname}"')
            if len(with_split) == 2:
                return f'UNKNOWN_MAPPING({with_split[0]}) WITH {with_split[1]}'
            else:
                return f'UNKNOWN_MAPPING({with_split[0]})'
        elif len(with_split) == 2:
            return f'{mapped_lic} WITH {with_split[1]}'
        else:
            return mapped_lic

    def map_license_string(self, pkgname, l_string, errors):
        ors = []
        for one_or in l_string.split(' or '):
            ands = []
            for one_and in one_or.split(' and '):
                ands.append(self.map_one_license_with_exception(pkgname, one_and, errors))
            ors.append(' AND '.join(ands))

        retval = ' OR '.join(ors)
        return retval

    def map_lic(self, pkgname, licenses, errors):
        if pkgname in self.perpackage_override:
            if self.perpackage_override[pkgname]:
                return self.perpackage_override[pkgname]

        retval = []
        for lic in licenses:
            if lic is not None:
                retval.append(self.map_license_string(pkgname, lic, errors))
            else:
                retval.append('Empty license')

        return retval


def scan_nomos(license_text):
    with NamedTemporaryFile() as f:
        f.write(license_text.encode('utf-8'))
        nomos_out = subprocess.run([
            '/usr/share/fossology/nomos/agent/nomos', f.name,
        ], check=True, capture_output=True, encoding='utf-8').stdout

    expected_start = f'File {os.path.basename(f.name)} contains license(s) '
    if not nomos_out.startswith(expected_start):
        raise Exception('nomos output error')

    licenses = nomos_out[len(expected_start):].strip()

    return licenses.split(',')


def license_string(pkg):
    if not pkg.has('spdx_licenses'):
        return 'NOASSERTION'

    l_list = []
    for ll in pkg.node('spdx_licenses'):
        if ll.et.text.find(' OR ') != -1:
            l_list.append('(' + ll.et.text + ')')
        else:
            l_list.append(ll.et.text)

    return ' AND '.join(l_list)


def run_command(argv):

    aparser = argparse.ArgumentParser(prog='elbe parselicence')
    aparser.add_argument('--output', dest='output',
                         help='outputfilename')
    aparser.add_argument('--mapping', dest='mapping',
                         required=True,
                         help='mapping filename')
    aparser.add_argument(
        '--use-nomos',
        action='store_true',
        dest='use_nomos',
        default=False,
        help='Use the external nomos tool on the copyright text, '
             'and record the ouput in out xml')
    aparser.add_argument(
        '--errors-only',
        action='store_true',
        dest='only_errors',
        default=False,
        help='Only Output Packages with errors, '
             'needing a fix in the mapping file')
    aparser.add_argument('--tvout', dest='tagvalue',
                         help='tag value output filename')

    aparser.add_argument('licencefile')

    args = aparser.parse_args(argv)

    tree = etree(args.licencefile)

    num_pkg = 0
    mr = 0
    hr = 0
    err_pkg = 0

    mapping = license_dep5_to_spdx(args.mapping)

    # Dont use direct iterator, because we might want to delete
    # elements, when --errors-only is active
    for pkg in list(tree.root):
        errors = []

        pkg_name = pkg.et.attrib['name']
        num_pkg += 1
        if pkg.has('machinereadable'):
            mr += 1

        if pkg.has('heuristics'):
            hr += 1
            if not mapping.have_override(pkg_name):
                errors.append(
                    f'no override for heuristics based package "{pkg_name}"')

        if mapping.have_override(pkg_name):
            pkg.append('have_override')

        if pkg.has('debian_licenses'):
            sp = pkg.ensure_child('spdx_licenses')
            sp.clear()
            sp.et.text = '\n'
            lics = []
            for lic in pkg.node('debian_licenses'):
                if lic.et.text in lics:
                    continue
                lics.append(lic.et.text)

            mapped_lics = mapping.map_lic(pkg_name, lics, errors)

            for lic in mapped_lics:
                ll = sp.append('license')
                ll.et.text = lic

            if not mapped_lics:
                errors.append(f'empty mapped licenses in package "{pkg_name}"')
        else:
            if not mapping.have_override(pkg_name):
                errors.append(
                    'no debian_licenses and no override in package '
                    f'"{pkg_name}"')
            else:
                sp = pkg.ensure_child('spdx_licenses')
                sp.clear()
                sp.et.text = '\n'
                for lic in mapping.get_override(pkg_name):
                    ll = sp.append('license')
                    ll.et.text = lic

        if args.use_nomos:
            nomos_l = scan_nomos(pkg.text('text'))
            if nomos_l[0] != 'No_license_found':
                nomos_node = pkg.append('nomos_licenses')
                nomos_node.et.text = '\n'
                for lic in nomos_l:
                    ll = nomos_node.append('license')
                    ll.et.text = lic

        if errors:
            for e in errors:
                ee = pkg.append('error')
                ee.et.text = e
            err_pkg += 1
        elif args.only_errors:
            # No Errors, and only_errors is active
            # Remove package node
            tree.root.remove_child(pkg)

    if args.tagvalue is not None:
        created = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds')
        with io.open(args.tagvalue, 'wt', encoding='utf-8') as fp:
            fp.write('SPDXVersion: SPDX-1.2\n')
            fp.write('DataLicense: CC0-1.0\n')
            fp.write('\n')
            fp.write('## Creation Information\n')
            fp.write(f'Creator: Tool: elbe-{elbe_version}\n')
            fp.write(f'Created: {created}\n')
            fp.write('\n')
            fp.write('\n')
            fp.write('## Package Information\n')
            fp.write('\n')

            for pkg in tree.root:
                fp.write(f"## Package {pkg.et.attrib['name']}\n")
                fp.write(f"PackageName: {pkg.et.attrib['name']}\n")
                fp.write('PackageDownloadLocation: NOASSERTION\n')
                if pkg.has('have_override'):
                    fp.write(
                        f'PackageLicenseConcluded: {license_string(pkg)}\n')
                    fp.write('PackageLicenseDeclared: NOASSERTION\n')

                else:
                    fp.write('PackageLicenseConcluded: NOASSERTION\n')
                    fp.write(
                        f'PackageLicenseDeclared: {license_string(pkg)}\n')
                fp.write('PackageLicenseInfoFromFiles: NOASSERTION\n')
                fp.write('\n')

    if args.output is not None:
        tree.write(args.output)

    print('statistics:')
    print(f'num:{num_pkg} mr:{mr} hr:{hr} err_pkg:{err_pkg}')
