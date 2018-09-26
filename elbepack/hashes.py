# ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (c) 2018 Torben Hohn <torben.hohn@linutronix.de>
#
# SPDX-License-Identifier: GPL-3.0-or-later

import hashlib
from shutil import copyfileobj

# different module names in python 2 and 3
try:
    import urllib.request

    # when running inside pylint this import fails
    # disable no-member here
    #
    # pylint: disable=no-member

    urlopen = urllib.request.urlopen
except ImportError:
    import urllib2
    urlopen = urllib2.urlopen


class HashValidationFailed(Exception):
    pass


def validate_sha256(fname, expected_hash):
    m = hashlib.sha256()
    with open(fname, "rb") as f:
        buf = f.read(65536)
        while buf:
            m.update(buf)
            buf = f.read(65536)
    if m.hexdigest() != expected_hash:
        raise HashValidationFailed(
                'file "%s" failed to verify ! got: "%s" expected: "%s"' %
                (fname, m.hexdigest(), expected_hash))


class HashValidator(object):
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
            rf = urlopen(url, None, 10)
            with open(local_fname, "w") as wf:
                copyfileobj(rf, wf)
        finally:
            rf.close()

        self.validate_file(upstream_fname, local_fname)
