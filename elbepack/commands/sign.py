# ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (C) 2014  Linutronix GmbH
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

import os
import sys
import elbepack
import gpgme

def sign_file(fname, fingerprint):
    outfilename = fname + '.gpg'
    ctx = gpgme.Context()
    ctx.armor = False

    try:
        key = ctx.get_key(fingerprint)
        try:
            infile = open(fname, 'r')
            try:
                outfile = open(outfilename, 'w')
                try:
                    ctx.sign(infile, outfile, gpgme.SIG_MODE_NORMAL)
                    print 'Signed file written to: %s' % outfilename
                    sys.exit(0)
                except Exception as ex:
                    print 'Error signing the file %s: %s' % (infilename, ex.message)
                    sys.exit(20)
            except IOError as ex:
                print 'Cannot open output file %s: %s' % (outfilename, ex.message)
                sys.exit(20)
        except IOError as ex:
            print 'Cannot open the file to sign: %s' % ex.message
            sys.exit(20)
    except gpgme.GpgmeError as ex:
        print 'Cannot find key with fingerprint %s: %s' % (fingerprint % ex.message)
        sys.exit(20)

def run_command( argv ):
    if(len(argv) != 2):
        print 'Wrong number of arguments.'
        print 'Please pass the name of the file to sign and a valid gnupg fingerprint.'
        sys.exit(20)
    else:
        sign_file( argv[0], argv[1])
