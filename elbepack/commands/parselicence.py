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
import datetime
import sys
import os
import io
import string

from tempfile import NamedTemporaryFile

from elbepack.asciidoclog import StdoutLog
from elbepack.elbexml import ElbeXML, ValidationError
from elbepack.treeutils import etree

from elbepack.filesystem import Filesystem
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
        print retval
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





def run_command( argv ):
    oparser = OptionParser(usage="usage: %prog parselicence [options] <licencefile>")
    oparser.add_option( "--output", dest="output",
                        help="outputfilename" )
    oparser.add_option( "--mapping", dest="mapping",
                        help="mapping filename" )

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

    mapping = license_dep5_to_spdx (opt.mapping)

    unknown_licenses = []
    for pkg in tree.root:
        errors = []

        pkg_name = pkg.et.attrib['name']
        num_pkg += 1
        if pkg.has('machinereadable'):
            mr += 1

        if pkg.has('heuristics'):
            hr += 1
            if not mapping.have_override (pkg_name):
                errors.append ('no override for heuristics based package "%s"' % pkg_name)

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
                errors.append ('no debian_licenses and no overrid in package "%s"' % pkg_name)
            else:
                sp = pkg.ensure_child ('spdx_licenses')
                sp.clear()
                sp.et.text = '\n'
                for l in mapping.get_override (pkg_name):
                    ll = sp.append('license')
                    ll.et.text=l

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



    print
    print "unknown_licenses"
    print "-------------------------------------------------------------------------"
    for l in set(unknown_licenses):
        print l

    if not opt.output is None:
        tree.write (opt.output)


    print "staistics:"
    print 'num:%d mr:%d hr:%d err_pkg:%d' % (num_pkg, mr, hr, err_pkg)

    return
    for pkg in tree.root:
        if pkg.has('machinereadable'):
            print '-----------------------------------------------------'
            print pkg.et.attrib['name']
            for l in pkg.node('debian_licenses'):
                print l.et.text
            print scan_nomos( pkg.text('text') )


    for pkg in tree.root:
        if pkg.has('heuristics'):
            print '-----------------------------------------------------'
            print pkg.et.attrib['name']
            for l in pkg.node('debian_licenses'):
                print l.et.text
            print scan_nomos( pkg.text('text') )


    for pkg in tree.root:
        pass



