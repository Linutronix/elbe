# ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (c) 2014 Andreas Messerschmid <andreas@linutronix.de>
# Copyright (c) 2014-2015, 2017 Manuel Traut <manut@linutronix.de>
# Copyright (c) 2016 Torben Hohn <torben.hohn@linutronix.de>
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import print_function

import os

from gpg import core
from gpg.constants import sigsum, sig

from elbepack.filesystem import hostfs
from elbepack.shellhelper import system

elbe_internal_key_param = """
<GnupgKeyParms format="internal">
  Key-Type: RSA
  Key-Usage: sign
  Key-Length: 2048
  Name-Real: Elbe Internal Repo
  Name-Comment: Automatically generated
  Name-Email: root@elbe-daemon.de
  Expire-Date: 0
  Passphrase: requiredToAvoidUserInput
</GnupgKeyParms>
"""


class OverallStatus(object):

    def __init__(self):
        self.invalid = False
        self.key_expired = False
        self.sig_expired = False
        self.key_revoked = False
        self.key_missing = False
        self.gpg_error = False

    def add(self, to_add):
        self.invalid = self.invalid or to_add.invalid
        self.key_expired = self.key_expired or to_add.key_expired
        self.sig_expired = self.sig_expired or to_add.sig_expired
        self.key_revoked = self.key_revoked or to_add.key_revoked
        self.key_missing = self.key_missing or to_add.key_missing
        self.gpg_error = self.gpg_error or to_add.gpg_error

    def to_exitcode(self):
        if self.gpg_error:      # critical GPG error
            return 20
        if self.invalid:        # invalid signature
            return 1
        if self.sig_expired or \
           self.key_expired or \
           self.key_revoked or \
           self.key_missing:
            return 2

        return 0


def check_signature(ctx, sig):
    status = OverallStatus()

    if sig.summary & sigsum.KEY_MISSING:
        print("Signature with unknown key: %s" % sig.fpr)
        status.key_missing = True
        return status

    # there should be a key
    key = ctx.get_key(sig.fpr, 0)
    print("%s <%s> (%s):" % (key.uids[0].name, key.uids[0].email, sig.fpr))
    if sig.summary & sigsum.VALID == sigsum.VALID:
        # signature fully valid and trusted
        print("VALID (Trusted)")
        return status

    # print detailed status in case it's not fully valid and trusted
    if sig.summary == 0:
        # Signature is valid, but the key is not ultimately trusted,
        # see: http://www.gossamer-threads.com/lists/gnupg/users/52350
        print("VALID (Untrusted).")
    if sig.summary & sigsum.SIG_EXPIRED == sigsum.SIG_EXPIRED:
        print("SIGNATURE EXPIRED!")
        status.sig_expired = True
    if sig.summary & sigsum.KEY_EXPIRED == sigsum.KEY_EXPIRED:
        print("KEY EXPIRED!")
        status.key_expired = True
    if sig.summary & sigsum.KEY_REVOKED == sigsum.KEY_REVOKED:
        print("KEY REVOKED!")
        status.key_revoked = True
    if sig.summary & sigsum.RED == sigsum.RED:
        print("INVALID SIGNATURE!")
        status.invalid = True
    if sig.summary & sigsum.CRL_MISSING == sigsum.CRL_MISSING:
        print("CRL MISSING!")
        status.gpg_error = True
    if sig.summary & sigsum.CRL_TOO_OLD == sigsum.CRL_TOO_OLD:
        print("CRL TOO OLD!")
        status.gpg_error = True
    if sig.summary & sigsum.BAD_POLICY == sigsum.BAD_POLICY:
        print("UNMET POLICY REQUIREMENT!")
        status.gpg_error = True
    if sig.summary & sigsum.SYS_ERROR == sigsum.SYS_ERROR:
        print("SYSTEM ERROR!'")
        status.gpg_error = True

    return status


def unsign_file(fname):
    # check for .gpg extension and create an output filename without it
    if len(fname) <= 4 or fname[len(fname) - 4:] != '.gpg':
        print("The input file needs a .gpg extension")
        return None

    outfilename = fname[:len(fname) - 4]

    os.environ['GNUPGHOME'] = "/var/cache/elbe/gnupg"
    ctx = core.Context()
    ctx.set_armor(False)

    try:
        overall_status = OverallStatus()

        with core.Data(file=fname) as infile:
            with core.Data(file=outfilename) as outfile:

                # obtain signature and write unsigned file
                ctx.op_verify(infile, None, outfile)
                vres = ctx.op_verify_result()

                for sig in vres.signatures:
                    status = check_signature(ctx, sig)
                    overall_status.add(status)

        if overall_status.to_exitcode():
            return None

        return outfilename

    except IOError as ex:
        print(ex.message)
    except Exception as ex:
        print("Error checking the file %s: %s" % (fname, ex.message))

    return None

def unlock_key(fingerprint):
    os.environ['GNUPGHOME'] = "/var/cache/elbe/gnupg"
    ctx = core.Context()
    key = ctx.get_key(fingerprint, secret=True)
    keygrip = key.subkeys[0].keygrip
    system("/usr/lib/gnupg2/gpg-preset-passphrase "
           "--preset -P requiredToAvoidUserInput %s" % str(keygrip),
           env_add={"GNUPGHOME": "/var/cache/elbe/gnupg"})

def sign(infile, outfile, fingerprint):

    os.environ['GNUPGHOME'] = "/var/cache/elbe/gnupg"
    ctx = core.Context()
    key = None

    try:
        key = ctx.get_key(fingerprint, 0)
    except Exception as ex:
        print("no key with fingerprint %s: %s" % (fingerprint, ex.message))

    unlock_key(key.fpr)
    ctx.signers_add(key)
    ctx.set_armor(False)

    try:
        indata = core.Data(file=infile)
        outdata = core.Data()
        ctx.op_sign(indata, outdata, sig.mode.NORMAL)
        outdata.seek(0, os.SEEK_SET)
        signature = outdata.read()
        with open(outfile, 'w') as fd:
            fd.write(signature)
    except Exception as ex:
        print("Error signing file %s" % ex.message)


def sign_file(fname, fingerprint):
    outfilename = fname + '.gpg'

    try:
        sign(fname, outfilename, fingerprint)
    except Exception as ex:
        print("Error signing file %s" % ex.message)


def get_fingerprints():
    os.environ['GNUPGHOME'] = "/var/cache/elbe/gnupg"
    ctx = core.Context()
    keys = ctx.op_keylist_all(None, False)
    fingerprints = []
    for k in keys:
        fingerprints.append(k.subkeys[0].fpr)
    return fingerprints


def generate_elbe_internal_key():
    hostfs.mkdir_p("/var/cache/elbe/gnupg")
    hostfs.write_file("/var/cache/elbe/gnupg/gpg-agent.conf", 0o600,
                      "allow-preset-passphrase")
    os.environ['GNUPGHOME'] = "/var/cache/elbe/gnupg"
    ctx = core.Context()
    ctx.op_genkey(elbe_internal_key_param, None, None)
    key = ctx.op_genkey_result()

    return key.fpr


def export_key(fingerprint, outfile):
    os.environ['GNUPGHOME'] = "/var/cache/elbe/gnupg"
    ctx = core.Context()
    ctx.set_armor(True)

    try:
        outdata = core.Data()
        ctx.op_export(fingerprint, 0, outdata)
        outdata.seek(0, os.SEEK_SET)
        key = outdata.read()
        outfile.write(key)
    except Exception:
        print("Error exporting key %s" % (fingerprint))

    return '/var/cache/elbe/gnupg/pubring.kbx'
