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

# Please note that to get VALID (Trusted), the key that the file was signed
# with has to have ultimate trust level, otherwise you'll only get
# VALID (Untrusted)!

import sys
import gpgme

class OverallStatus:

    def __init__(self):
        self.invalid = False
        self.key_expired = False
        self.sig_expired = False
        self.key_revoked = False
        self.key_missing = False
        self.gpgme_error = False

    def add(self, to_add):
        self.invalid = self.invalid or to_add.invalid
        self.key_expired = self.key_expired or to_add.key_expired
        self.sig_expired = self.sig_expired or to_add.sig_expired
        self.key_revoked = self.key_revoked or to_add.key_revoked
        self.key_missing = self.key_missing or to_add.key_missing
        self.gpgme_error = self.gpgme_error or to_add.gpgme_error

    def to_exitcode(self):
        if self.gpgme_error:    # critical GPG error
            return 20
        if self.invalid:        # invalid signature
            return 1
        if self.sig_expired or self.key_expired or self.key_revoked or self.key_missing:
            return 2
        return 0

def check_signature(ctx, sig):
    status = OverallStatus()
    if sig.summary & gpgme.SIGSUM_KEY_MISSING == 0:
        # there should be a key
        key = ctx.get_key(sig.fpr)
        print '%s <%s> (%s):' % (key.uids[0].name, key.uids[0].email, sig.fpr),
        if sig.summary & gpgme.SIGSUM_VALID == gpgme.SIGSUM_VALID:
            # signature fully valid and trusted
            print 'VALID (Trusted)'
        else:
            # print detailed status in case it's not fully valid and trusted
            if sig.summary == 0:
                # Signature is valid, but the key is not ultimately trusted,
                # see: http://www.gossamer-threads.com/lists/gnupg/users/52350
                print 'VALID (Untrusted).',
            if sig.summary & gpgme.SIGSUM_SIG_EXPIRED == gpgme.SIGSUM_SIG_EXPIRED:
                print 'SIGNATURE EXPIRED!',
                status.sig_expired = True
            if sig.summary & gpgme.SIGSUM_KEY_EXPIRED == gpgme.SIGSUM_KEY_EXPIRED:
                print 'KEY EXPIRED!',
                status.key_expired = True
            if sig.summary & gpgme.SIGSUM_KEY_REVOKED == gpgme.SIGSUM_KEY_REVOKED:
                print 'KEY REVOKED!',
                status.key_revoked = True
            if sig.summary & gpgme.SIGSUM_RED == gpgme.SIGSUM_RED:
                print 'INVALID SIGNATURE!',
                status.invalid = True
            if sig.summary & gpgme.SIGSUM_CRL_MISSING == gpgme.SIGSUM_CRL_MISSING:
                print 'CRL MISSING!',
                status.gpgme_error = True
            if sig.summary & gpgme.SIGSUM_CRL_TOO_OLD == gpgme.SIGSUM_CRL_TOO_OLD:
                print 'CRL TOO OLD!',
                status.gpgme_error = True
            if sig.summary & gpgme.SIGSUM_BAD_POLICY == gpgme.SIGSUM_BAD_POLICY:
                print 'UNMET POLICY REQUIREMENT!',
                status.gpgme_error = True
            if sig.summary & gpgme.SIGSUM_SYS_ERROR == gpgme.SIGSUM_SYS_ERROR:
                print 'SYSTEM ERROR!',
                status.gpgme_error = True
            print
    else:
        print 'Signature with unknown key: %s' % sig.fpr
        status.key_missing = True
    return status


def unsign_file(fname):
    # check for .gpg extension and create an output filename without it
    if len(fname) <= 4 or fname[len(fname)-4:] != '.gpg':
        print 'The input file needs a .gpg extension'
        sys.exit(20)
    outfilename = fname[:len(fname)-4]

    ctx = gpgme.Context()
    ctx.armor = False

    try:
        infile = open(fname, 'r')
        try:
            outfile = open(outfilename, 'w')
            try:
                # obtain signature and write unsigned file
                sigs = ctx.verify(infile, None, outfile)
                print 'Unsigned file written into file: %s' % outfilename

                # print status of all signatures and check if all signatures are valid
                overall_status = OverallStatus()
                print 'Signatures found:'
                for sig in sigs:
                    overall_status.add(check_signature(ctx, sig))

                sys.exit(overall_status.to_exitcode())
            except Exception as ex:
                print 'Error checking the file %s: %s' % (fname, ex.message)
                sys.exit(20)
        except IOError as ex:
            print 'Cannot open output file %s: %s' % (outfilename, ex.message)
            sys.exit(20)
    except IOError as ex:
        print 'Cannot open the file to read from: %s' % ex.message
        sys.exit(20)

def run_command( argv ):
    if(len(argv) != 1):
        print 'Wrong number of arguments.'
        print 'Please pass the name of the file to unsign.'
        sys.exit(20)
    else:
        unsign_file( argv[0] )
