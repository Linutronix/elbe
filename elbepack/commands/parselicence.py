# ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (c) 2016 Torben Hohn <torben.hohn@linutronix.de>
# Copyright (c) 2017 Manuel Traut <manut@linutronix.de>
#
# SPDX-License-Identifier: GPL-3.0-or-later

from optparse import OptionParser
from datetime import datetime
import sys
import os
import io

from tempfile import NamedTemporaryFile

from elbepack.treeutils import etree
from elbepack.version import elbe_version
from elbepack.shellhelper import system_out


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

    def map_one_license(self, pkgname, l, errors):
        if pkgname in self.perpackage_mapping:
            if l in self.perpackage_mapping[pkgname]:
                return self.perpackage_mapping[pkgname][l]
        if l in self:
            return self[l]
        errors.append(f'no mapping for "{l}" for pkg "{pkgname}"')
        return None

    def map_license_string(self, pkgname, l_string, errors):
        ors = []
        for one_or in l_string.split(' or '):
            ands = []
            for one_and in one_or.split(' and '):
                with_split = one_and.split(' with ')
                mapped_lic = self.map_one_license(
                    pkgname, with_split[0], errors)
                if mapped_lic is None:
                    mapped_lic = f"UNKNOWN_MAPPING({with_split[0]})"
                if len(with_split) == 2:
                    ands.append(f"{mapped_lic} WITH {with_split[1]}")
                else:
                    ands.append(mapped_lic)
            ors.append(' AND '.join(ands))

        retval = ' OR '.join(ors)
        return retval

    def map_lic(self, pkgname, licenses, errors):
        if pkgname in self.perpackage_override:
            if self.perpackage_override[pkgname]:
                return self.perpackage_override[pkgname]

        retval = []
        for l in licenses:
            if l is not None:
                retval.append(self.map_license_string(pkgname, l, errors))
            else:
                retval.append('Empty license')

        return retval


def scan_nomos(license_text):
    with NamedTemporaryFile() as f:
        f.write(license_text.encode('utf-8'))
        nomos_out = system_out(
            f'/usr/share/fossology/nomos/agent/nomos "{f.name}"')

    expected_start = f'File {os.path.basename(f.name)} contains license(s) '
    if not nomos_out.startswith(expected_start):
        raise Exception("nomos output error")

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

    # pylint: disable=too-many-locals
    # pylint: disable=too-many-statements
    # pylint: disable=too-many-branches

    oparser = OptionParser(
        usage="usage: %prog parselicence [options] <licencefile>")
    oparser.add_option("--output", dest="output",
                       help="outputfilename")
    oparser.add_option("--mapping", dest="mapping",
                       help="mapping filename")
    oparser.add_option(
        "--use-nomos",
        action="store_true",
        dest="use_nomos",
        default=False,
        help="Use the external nomos tool on the copyright text, "
             "and record the ouput in out xml")
    oparser.add_option(
        "--errors-only",
        action="store_true",
        dest="only_errors",
        default=False,
        help="Only Output Packages with errors, "
             "needing a fix in the mapping file")
    oparser.add_option("--tvout", dest="tagvalue",
                       help="tag value output filename")

    (opt, args) = oparser.parse_args(argv)

    if len(args) != 1:
        print("wrong number of arguments")
        oparser.print_help()
        sys.exit(20)

    tree = etree(args[0])

    num_pkg = 0
    mr = 0
    hr = 0
    err_pkg = 0

    if not opt.mapping:
        print("A mapping file is required")
        oparser.print_help()
        sys.exit(20)

    mapping = license_dep5_to_spdx(opt.mapping)

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
            for l in pkg.node('debian_licenses'):
                if l.et.text in lics:
                    continue
                lics.append(l.et.text)

            mapped_lics = mapping.map_lic(pkg_name, lics, errors)

            for l in mapped_lics:
                ll = sp.append('license')
                ll.et.text = l

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
                for l in mapping.get_override(pkg_name):
                    ll = sp.append('license')
                    ll.et.text = l

        if opt.use_nomos:
            nomos_l = scan_nomos(pkg.text('text'))
            if nomos_l[0] != 'No_license_found':
                nomos_node = pkg.append('nomos_licenses')
                nomos_node.et.text = '\n'
                for l in nomos_l:
                    ll = nomos_node.append('license')
                    ll.et.text = l

        if errors:
            for e in errors:
                ee = pkg.append('error')
                ee.et.text = e
            err_pkg += 1
        elif opt.only_errors:
            # No Errors, and only_errors is active
            # Remove package node
            tree.root.remove_child(pkg)

    if opt.tagvalue is not None:
        with io.open(opt.tagvalue, "wt", encoding='utf-8') as fp:
            fp.write('SPDXVersion: SPDX-1.2\n')
            fp.write('DataLicense: CC0-1.0\n')
            fp.write('\n')
            fp.write('## Creation Information\n')
            fp.write(f'Creator: Tool: elbe-{elbe_version}\n')
            fp.write(f'Created: {datetime.now().isoformat()}\n')
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

    if opt.output is not None:
        tree.write(opt.output)

    print("statistics:")
    print(f"num:{num_pkg} mr:{mr} hr:{hr} err_pkg:{err_pkg}")
