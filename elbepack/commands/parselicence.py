# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2016-2017 Linutronix GmbH

import argparse
import dataclasses
import datetime
import enum
import io
import os
import subprocess
from tempfile import NamedTemporaryFile

from elbepack.spdx import SPDX_LICENSE_IDENTIFIERS
from elbepack.treeutils import etree
from elbepack.version import elbe_version


@dataclasses.dataclass
class Statistics:
    total_pkgs: int = 0
    num_machine_readable: int = 0
    num_heuristics: int = 0
    num_error_pkgs: int = 0

    def __str__(self):
        return ' '.join([f'{k}={v}' for k, v in dataclasses.asdict(self).items()])


class LicenseType(enum.Enum):
    SPDX = enum.auto()
    SPDX_EXCEPTION = enum.auto()
    UNKNOWN = enum.auto()


@dataclasses.dataclass
class License:
    type: LicenseType
    name: str
    text: str


class license_dep5_to_spdx (dict):
    def __init__(self, xml_fname=None):
        super().__init__()

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
        if lic in SPDX_LICENSE_IDENTIFIERS:
            return lic
        return None

    def map_one_license_with_exception(self, pkgname, lic, errors):
        mapped_lic = self.map_one_license(pkgname, lic)
        if mapped_lic is not None:
            return mapped_lic

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


def _apply_mapping(licenses, mapping, *, use_nomos=False, only_errors=False):
    for pkg in list(licenses.root):
        errors = []

        pkg_name = pkg.et.attrib['name']

        if pkg.has('heuristics'):
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

        if errors:
            for e in errors:
                ee = pkg.append('error')
                ee.et.text = e
        elif only_errors:
            # No Errors, and only_errors is active
            # Remove package node
            licenses.root.remove_child(pkg)

        if use_nomos:
            nomos_l = scan_nomos(pkg.text('text'))
            if nomos_l[0] != 'No_license_found':
                nomos_node = pkg.append('nomos_licenses')
                nomos_node.et.text = '\n'
                for lic in nomos_l:
                    ll = nomos_node.append('license')
                    ll.et.text = lic


def _compute_statistics(licenses):
    statistics = Statistics()
    for pkg in list(licenses.root):

        statistics.total_pkgs += 1

        if pkg.has('machinereadable'):
            statistics.num_machine_readable += 1

        if pkg.has('heuristics'):
            statistics.num_heuristics += 1

        if pkg.has('error'):
            statistics.num_error_pkgs += 1

    return statistics


def extract_licenses_from_report(licence_file, mapping_file):
    extracted_licenses = {}
    licenses = etree(licence_file)
    mapping = license_dep5_to_spdx(mapping_file)
    _apply_mapping(licenses, mapping)
    for pkg in list(licenses.root):

        pkg_name = pkg.et.attrib['name']

        if pkg.has('spdx_licenses'):

            licenses = []
            for ll in pkg.node('spdx_licenses'):
                if ll.et.text.find('UNKNOWN_MAPPING') != -1:
                    license = License(name=ll.et.text.replace(
                                      'UNKNOWN_MAPPING(', '').replace(')', ''),
                                      type=LicenseType.UNKNOWN,
                                      text=pkg.node('text').et.text)
                elif ll.et.text.find(' AND ') != -1:
                    temp = ll.et.text.split(' AND ')
                    for i in temp:
                        license = License(name=i,
                                          type=LicenseType.SPDX,
                                          text=None)
                elif ll.et.text.find(' WITH ') != -1:
                    license = License(name=ll.et.text,
                                      type=LicenseType.SPDX_EXCEPTION,
                                      text=None)
                elif ll.et.text.find(' OR ') != -1:
                    license = License(name=ll.et.text,
                                      type=LicenseType.UNKNOWN,
                                      text=pkg.node('text').et.text)
                elif ll.et.text == 'Empty license':
                    license = None
                else:
                    license = License(name=ll.et.text,
                                      type=LicenseType.SPDX,
                                      text=None)

                licenses.append(license)

        errors = []
        if pkg.has('error'):
            for error in pkg.all('error'):
                if error.et.text not in errors:
                    errors.append(error.et.text)

        extracted_licenses[pkg_name] = (licenses, errors)

    return extracted_licenses


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

    mapping = license_dep5_to_spdx(args.mapping)

    _apply_mapping(tree, mapping, use_nomos=args.use_nomos, only_errors=args.only_errors)
    statistics = _compute_statistics(tree)

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
    print(statistics)
