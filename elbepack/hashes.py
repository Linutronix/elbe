# ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (c) 2018 Torben Hohn <torben.hohn@linutronix.de>
#
# SPDX-License-Identifier: GPL-3.0-or-later

import hashlib
from elbepack.shellhelper import system, CommandError


class HashValidationFailed(Exception):
    pass


def get_sha256(fname):
    m = hashlib.sha256()
    with open(fname, "rb") as f:
        buf = f.read(65536)
        while buf:
            m.update(buf)
            buf = f.read(65536)
    return m.hexdigest()

def validate_sha256(fname, expected_hash):
    if get_sha256(fname) != expected_hash:
        raise HashValidationFailed(
                'file "%s" failed to verify ! got: "%s" expected: "%s"' %
                (fname, m.hexdigest(), expected_hash))

class HashValidator:
    def __init__(self, base_url):
        self.hashes = {}
        self.base_url = base_url

    def insert_fname_hash(self, algo, fname, hash_val):
        if algo not in self.hashes:
            self.hashes[algo] = {}

        self.hashes[algo][fname] = hash_val

    def validate_file(self, upstream_fname, local_fname):
        if upstream_fname not in self.hashes['SHA256']:
            raise HashValidationFailed('Value to expect for "%s" is not known')

        validate_sha256(local_fname, self.hashes['SHA256'][upstream_fname])

    def download_and_validate_file(self, upstream_fname, local_fname):
        url = self.base_url + upstream_fname
        try:
            system('wget -O "%s" "%s"' % (local_fname, url))
        except CommandError:
            raise HashValidationFailed('Failed to download %s' % url)

        self.validate_file(upstream_fname, local_fname)
