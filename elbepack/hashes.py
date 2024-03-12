# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2018 Linutronix GmbH

import hashlib
import subprocess

from elbepack.shellhelper import system


class HashValidationFailed(Exception):
    pass


def validate_sha256(fname, expected_hash):
    m = hashlib.sha256()
    with open(fname, 'rb') as f:
        buf = f.read(65536)
        while buf:
            m.update(buf)
            buf = f.read(65536)
    if m.hexdigest() != expected_hash:
        raise HashValidationFailed(
                f'file "{fname}" failed to verify ! got: "{m.hexdigest()}" '
                f'expected: "{expected_hash}"')


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
            system(f'wget -O "{local_fname}" "{url}"')
        except subprocess.CalledProcessError as e:
            raise HashValidationFailed(f'Failed to download {url}') from e

        self.validate_file(upstream_fname, local_fname)
