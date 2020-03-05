# ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (c) 2020 Olivier Dion <dion@linutronix.de>
# Copyright (c) 2020 Torben Hohn <torbenh@linutronix.de>
#
# SPDX-License-Identifier: GPL-3.0-or-later

import unittest

from elbepack.version import elbe_version

# Since this is just an example on how to make tests, we skip them
class TestElbepackVersion(unittest.TestCase):

    # This is a read-only state that is the same for every tests
    expected_version = "12.3"

    def setUp(self):
        # This is a mutable state that is different for every tests
        self.my_list = []

    def tearDown(self):
        # You might want to cleanup your mutable states here
        pass

    @unittest.skip
    def test_version(self):
        self.my_list.append(1)
        self.assertEqual(elbe_version, self.expected_version)

    @unittest.skip
    def test_mutable_state(self):
        self.assertEqual(len(self.my_list), 0)
