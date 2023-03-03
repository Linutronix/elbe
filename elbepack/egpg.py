# ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (c) 2014 Andreas Messerschmid <andreas@linutronix.de>
# Copyright (c) 2014-2015, 2017 Manuel Traut <manut@linutronix.de>
# Copyright (c) 2016 Torben Hohn <torben.hohn@linutronix.de>
#
# SPDX-License-Identifier: GPL-3.0-or-later

import logging
import os

from gpg import core
from gpg.constants import sigsum, sig, PROTOCOL_OpenPGP
from gpg.errors import GPGMEError, KeyNotFound, InvalidSigners

from elbepack.filesystem import hostfs
from elbepack.shellhelper import get_command_out, system

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

# pylint: disable=too-many-instance-attributes
class OverallStatus:

    def __init__(self):
        self.invalid = 0
        self.key_expired = 0
        self.sig_expired = 0
        self.key_revoked = 0
        self.key_missing = 0
        self.gpg_error = 0
        self.valid = 0
        self.valid_threshold = 0

    def add(self, to_add):
        self.invalid += to_add.invalid
        self.key_expired += to_add.key_expired
        self.sig_expired += to_add.sig_expired
        self.key_revoked += to_add.key_revoked
        self.key_missing += to_add.key_missing
        self.gpg_error += to_add.gpg_error
        self.valid += to_add.valid
        self.valid_threshold += to_add.valid_threshold

    def to_exitcode(self):
        if self.gpg_error:      # critical GPG error
            return 20
        if self.invalid:        # invalid signature
            return 1
        if self.key_missing:
            return 2
        # The number of valid keys must always be greater or equal
        # than valid_threshold.
        #
        # Example for 8 keys:
        #
        # Valid    - self.valid = 1
        # Expired  - self.valid_threshold = 1
        # Valid    - self.valid = 2
        # Revoked  - self.valid_threshold = 2
        # Revoked  - self.valid_threshold = 3
        # Expired  - self.valid_threshold = 4
        # Valid    - self.valid = 3
        # Valid    - self.valid = 4
        #
        # This ensure that the number of valid keys is _always_ over
        # 50%.
        if self.valid < self.valid_threshold:
            return 2
        return 0


def check_signature(ctx, signature):
    status = OverallStatus()

    if signature.summary & sigsum.KEY_MISSING:
        print(f"Signature with unknown key: {signature.fpr}")
        status.key_missing = 1
        return status

    # there should be a key
    key = ctx.get_key(signature.fpr, 0)
    print(f"{key.uids[0].name} <{key.uids[0].email}> ({signature.fpr}):")

    if signature.summary & sigsum.VALID == sigsum.VALID:
        # signature fully valid and trusted
        print("VALID (Trusted)")
        status.valid = 1
        return status

    # print detailed status in case it's not fully valid and trusted
    if signature.summary == 0:
        # Signature is valid, but the key is not ultimately trusted,
        # see: http://www.gossamer-threads.com/lists/gnupg/users/52350
        print("VALID (Untrusted).")
        status.valid = 1

    if signature.summary & sigsum.SIG_EXPIRED == sigsum.SIG_EXPIRED:
        print("SIGNATURE EXPIRED!")
        status.sig_expired = 1
        status.valid_threshold = 1

    if signature.summary & sigsum.KEY_EXPIRED == sigsum.KEY_EXPIRED:
        print("KEY EXPIRED!")
        status.key_expired = 1
        status.valid_threshold = 1

    if signature.summary & sigsum.KEY_REVOKED == sigsum.KEY_REVOKED:
        print("KEY REVOKED!")
        status.key_revoked = 1
        status.valid_threshold = 1

    if signature.summary & sigsum.RED == sigsum.RED:
        print("INVALID SIGNATURE!")
        status.invalid = 1

    if signature.summary & sigsum.CRL_MISSING == sigsum.CRL_MISSING:
        print("CRL MISSING!")
        status.gpg_error = 1

    if signature.summary & sigsum.CRL_TOO_OLD == sigsum.CRL_TOO_OLD:
        print("CRL TOO OLD!")
        status.gpg_error = 1

    if signature.summary & sigsum.BAD_POLICY == sigsum.BAD_POLICY:
        print("UNMET POLICY REQUIREMENT!")
        status.gpg_error = 1

    if signature.summary & sigsum.SYS_ERROR == sigsum.SYS_ERROR:
        print("SYSTEM ERROR!'")
        status.gpg_error = 1

    return status


def unsign_file(fname):
    # check for .gpg extension and create an output filename without it
    if len(fname) <= 4 or fname[len(fname) - 4:] != '.gpg':
        print("The input file needs a .gpg extension")
        return None

    outfilename = fname[:len(fname) - 4]

    ctx = core.Context()
    ctx.set_engine_info(PROTOCOL_OpenPGP,
                        None,
                        '/var/cache/elbe/gnupg')
    ctx.set_armor(False)

    overall_status = OverallStatus()

    try:
        infile  = core.Data(file=fname)
        outfile = core.Data(file=outfilename)
    except (GPGMEError, ValueError) as E:
        print(f"Error: Opening file {fname} or {outfilename} - {E}")
    else:
        # obtain signature and write unsigned file
        ctx.op_verify(infile, None, outfile)
        vres = ctx.op_verify_result()

        for signature in vres.signatures:
            status = check_signature(ctx, signature)
            overall_status.add(status)

        if overall_status.to_exitcode():
            return None

        return outfilename

    return None

def unlock_key(fingerprint):
    ctx = core.Context()
    ctx.set_engine_info(PROTOCOL_OpenPGP,
                        None,
                        '/var/cache/elbe/gnupg')
    key = ctx.get_key(fingerprint, secret=True)
    keygrip = key.subkeys[0].keygrip
    system("/usr/lib/gnupg/gpg-preset-passphrase "
           f"--preset -P requiredToAvoidUserInput {keygrip}",
           env_add={"GNUPGHOME": "/var/cache/elbe/gnupg"})

def sign(infile, outfile, fingerprint):

    ctx = core.Context()

    try:
        ctx.set_engine_info(PROTOCOL_OpenPGP,
                            None,
                            '/var/cache/elbe/gnupg')
    except GPGMEError as E:
        print("Error: Can't set engine info - %s", E)
        return

    key = None

    try:
        key = ctx.get_key(fingerprint, 0)
    except (KeyNotFound, GPGMEError, AssertionError) as E:
        print(f"Error: No key with fingerprint {fingerprint} - {E}")
        return
    else:
        unlock_key(key.fpr)
        ctx.signers_add(key)
        ctx.set_armor(False)

    try:
        indata = core.Data(file=infile)
    except (GPGMEError, ValueError) as E:
        print(f"Error: Opening file {infile} - {E}")
    else:
        outdata = core.Data()
        try:
            ctx.op_sign(indata, outdata, sig.mode.NORMAL)
        except InvalidSigners as E:
            print("Error: Invalid signer - %s", E)
        except GPGMEError as E:
            print("Error: While signing - %s", E)
        else:
            outdata.seek(0, os.SEEK_SET)
            signature = outdata.read()
            with open(outfile, 'w') as fd:
                fd.write(signature)

def sign_file(fname, fingerprint):
    outfilename = fname + '.gpg'
    sign(fname, outfilename, fingerprint)

def get_fingerprints():
    ctx = core.Context()
    ctx.set_engine_info(PROTOCOL_OpenPGP,
                        None,
                        '/var/cache/elbe/gnupg')
    keys = ctx.op_keylist_all(None, False)
    fingerprints = []
    for k in keys:
        fingerprints.append(k.subkeys[0].fpr)
    return fingerprints

# End Of Time - Roughtly 136 years
#
# The argument parser of GPG use the type unsigned long for
# default-cache-ttl and max-cache-ttl values.  Thus we're setting the
# least maximum value of the type unsigned long to ensure that the
# passphrase is 'never' removed from gpg-agent.
EOT = 4294967295
def generate_elbe_internal_key():
    hostfs.mkdir_p("/var/cache/elbe/gnupg")
    hostfs.write_file("/var/cache/elbe/gnupg/gpg-agent.conf", 0o600,
                      "allow-preset-passphrase\n"
                      f"default-cache-ttl {EOT}\n"
                      f"max-cache-ttl {EOT}\n")
    ctx = core.Context()
    ctx.set_engine_info(PROTOCOL_OpenPGP,
                        None,
                        '/var/cache/elbe/gnupg')
    ctx.op_genkey(elbe_internal_key_param, None, None)
    key = ctx.op_genkey_result()

    return key.fpr


def export_key(fingerprint, outfile):
    system(f"/usr/bin/gpg -a -o {outfile} --export {fingerprint}",
           env_add={"GNUPGHOME": "/var/cache/elbe/gnupg"})

def unarmor_openpgp_keyring(armored):
    """
    Unarmors one ascii-armored (string) OpenPGP keyring.
    Returns a binary string (empty for invalid keys).
    """
    try:
        conv_cmd = get_command_out('/usr/bin/gpg --no-options --dearmor', stdin=armored)
    except CommandError as e:
        logging.error(e)
        return b""

    return conv_cmd
