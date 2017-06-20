# ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (C) 2013  Linutronix GmbH
#
# This file is part of ELBE.
#
# ELBE is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# ELBE is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with ELBE.  If not, see <http://www.gnu.org/licenses/>.


from optparse import OptionParser
from datetime import datetime
import sys
import os
import io
import string

from tempfile import NamedTemporaryFile

from elbepack.treeutils import etree
from elbepack.version import elbe_version
from elbepack.shellhelper import system_out

class license_dep5_to_spdx (dict):
    def __init__ (self, xml_fname=None):
        self.perpackage_mapping = {}
        self.perpackage_override = {}
        if xml_fname is None:
            return

        xml = etree (xml_fname)

        if xml.root.has ('global'):
            for mapping in xml.root.node('global'):
                self[mapping.et.attrib['name']] = mapping.et.text

        if xml.root.has ('perpackage'):
            for pkg in xml.root.node('perpackage'):
                pname = pkg.et.attrib['name']
                self.perpackage_mapping[pname] = {}
                self.perpackage_override[pname] = []
                for pp in pkg:
                    if pp.tag == 'mapping':
                        self.perpackage_mapping[pname][pp.et.attrib['name']] = pp.et.text
                    if pp.tag == 'license':
                        self.perpackage_override[pname].append (pp.et.text)


    def have_override (self, pkgname):
        return self.perpackage_override.has_key (pkgname)

    def get_override (self, pkgname):
        return self.perpackage_override[pkgname]

    def map_one_license (self, pkgname, l, errors):
        if self.perpackage_mapping.has_key(pkgname):
            if self.perpackage_mapping[pkgname].has_key(l):
                return self.perpackage_mapping[pkgname][l]
        if self.has_key(l):
            return self[l]
        errors.append ('no mapping for "%s" for pkg "%s"' % (l, pkgname))
        return None

    def map_license_string (self, pkgname, l_string, errors):
        ors = []
        for one_or in l_string.split(' or '):
            ands = []
            for one_and in one_or.split (' and '):
                with_split = one_and.split (' with ')
                mapped_lic = self.map_one_license (pkgname, with_split[0], errors)
                if mapped_lic is None:
                    mapped_lic = u"UNKNOWN_MAPPING(%s)" % with_split[0]
                if len (with_split) == 2:
                    ands.append (mapped_lic + u" WITH " + with_split[1])
                else:
                    ands.append (mapped_lic)
            ors.append (string.join (ands, u' AND '))

        retval = string.join (ors, u' OR ')
        return retval




    def map_lic (self, pkgname, licenses, errors):
        if self.perpackage_override.has_key (pkgname):
            if len(self.perpackage_override[pkgname]) > 0:
                return self.perpackage_override[pkgname]

        retval = []
        for l in licenses:
            if l is not None:
                retval.append (self.map_license_string (pkgname, l, errors))
            else:
                retval.append ('Empty license')

        return retval







def scan_nomos ( license_text ):
    with NamedTemporaryFile() as f:
        f.write (license_text.encode('utf-8'))
        nomos_out = system_out ('/usr/share/fossology/nomos/agent/nomos "%s"' % f.name)

    expected_start = 'File %s contains license(s) ' % os.path.basename(f.name)
    if not nomos_out.startswith (expected_start):
        raise Exception("nomos output error")

    licenses = nomos_out [len(expected_start):].strip()

    return licenses.split(',')


def license_string (pkg):
    if not pkg.has ('spdx_licenses'):
        return 'NOASSERTION'

    l_list = []
    for ll in pkg.node('spdx_licenses'):
        if ll.et.text.find (' OR ') != -1:
            l_list.append ('('+ll.et.text+')')
        else:
            l_list.append (ll.et.text)

    return string.join (l_list, ' AND ')





def run_command( argv ):
    oparser = OptionParser(usage="usage: %prog parselicence [options] <licencefile>")
    oparser.add_option( "--output", dest="output",
                        help="outputfilename" )
    oparser.add_option( "--mapping", dest="mapping",
                        help="mapping filename" )
    oparser.add_option( "--use-nomos", action="store_true",
                        dest="use_nomos", default=False,
                        help="Use the external nomos tool on the copyright text, and record the ouput in out xml" )
    oparser.add_option( "--errors-only", action="store_true",
                        dest="only_errors", default=False,
                        help="Only Output Packages with errors, needing a fix in the mapping file" )
    oparser.add_option( "--tvout", dest="tagvalue",
                        help="tag value output filename" )

    (opt,args) = oparser.parse_args(argv)

    if len(args) != 1:
        print "wrong number of arguments"
        oparser.print_help()
        sys.exit(20)

    tree = etree(args[0])

    num_pkg = 0
    mr = 0
    hr = 0
    err_pkg = 0

    if not opt.mapping:
        print "A mapping file is required"
        oparser.print_help()
        sys.exit(20)

    mapping = license_dep5_to_spdx (opt.mapping)

    unknown_licenses = []
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
            if not mapping.have_override (pkg_name):
                errors.append ('no override for heuristics based package "%s"' % pkg_name)

        if mapping.have_override (pkg_name):
            pkg.append ('have_override')

        if pkg.has('debian_licenses'):
            sp = pkg.ensure_child ('spdx_licenses')
            sp.clear()
            sp.et.text = '\n'
            lics = []
            for l in pkg.node('debian_licenses'):
                if l.et.text in lics:
                    continue
                lics.append (l.et.text)

            mapped_lics = mapping.map_lic (pkg_name, lics, errors)

            for l in mapped_lics:
                ll = sp.append('license')
                ll.et.text=l

            if len(mapped_lics) == 0:
                errors.append ('empty mapped licenses in package "%s"' % pkg_name)
        else:
            if not mapping.have_override (pkg_name):
                errors.append ('no debian_licenses and no override in package "%s"' % pkg_name)
            else:
                sp = pkg.ensure_child ('spdx_licenses')
                sp.clear()
                sp.et.text = '\n'
                for l in mapping.get_override (pkg_name):
                    ll = sp.append('license')
                    ll.et.text=l

        if opt.use_nomos:
            nomos_l = scan_nomos( pkg.text('text') )
            if nomos_l[0] != 'No_license_found':
                nomos_node = pkg.append ('nomos_licenses')
                nomos_node.et.text='\n'
                for l in nomos_l:
                    ll = nomos_node.append ('license')
                    ll.et.text = l

        if len (errors) > 0:
            for e in errors:
                ee = pkg.append ('error')
                ee.et.text=e
            err_pkg += 1
        elif opt.only_errors:
            # No Errors, and only_errors is active
            # Remove package node
            tree.root.remove_child (pkg)

    if not opt.tagvalue is None:
        with io.open (opt.tagvalue, "wt", encoding='utf-8') as fp:
            fp.write (u'SPDXVersion: SPDX-1.2\n')
            fp.write (u'DataLicense: CC0-1.0\n')
            #fp.write (u'SPDXID: SPDXRef-DOCUMENT\n')
            #fp.write (u'DocumentName: %s\n' % opt.tagvalue)
            #fp.write (u'DocumentNamespace: %s\n' % some_uri_with_uuid )
            fp.write (u'\n')
            fp.write (u'## Creation Information\n')
            fp.write (u'Creator: Tool: elbe-%s\n' % elbe_version )
            fp.write (u'Created: %s\n' % datetime.now().isoformat() )
            fp.write (u'\n' )
            fp.write (u'\n' )
            fp.write (u'## Package Information\n' )
            fp.write (u'\n' )

            for pkg in tree.root:
                fp.write (u'## Package %s\n' % pkg.et.attrib['name'] )
                fp.write (u'PackageName: %s\n' % pkg.et.attrib['name'])
                fp.write (u'PackageDownloadLocation: NOASSERTION\n')
                #fp.write (u'PackageVerificationCode: %s\n')
                if pkg.has ('have_override'):
                    fp.write (u'PackageLicenseConcluded: %s\n' % license_string (pkg))
                    fp.write (u'PackageLicenseDeclared: NOASSERTION\n')

                else:
                    fp.write (u'PackageLicenseConcluded: NOASSERTION\n')
                    fp.write (u'PackageLicenseDeclared: %s\n' % license_string (pkg))
                fp.write (u'PackageLicenseInfoFromFiles: NOASSERTION\n')
                fp.write (u'\n' )




    if not opt.output is None:
        tree.write (opt.output)


    print "statistics:"
    print 'num:%d mr:%d hr:%d err_pkg:%d' % (num_pkg, mr, hr, err_pkg)



