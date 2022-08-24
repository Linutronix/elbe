# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2020 Linutronix GmbH

import unittest

from elbepack.filesystem import TmpdirFilesystem
from elbepack.efilesystem import copy_filelist

class TestCopyFilelist(unittest.TestCase):

    def setUp(self):
        self.src = TmpdirFilesystem()
        self.dst = TmpdirFilesystem()

    def tearDown(self):
        del self.src
        del self.dst

    def test_usrmerge_abs(self):

        self.src.mkdir_p('/usr/bin')

        # this will link to /usr/bin in the host RFS,
        # when no special logic is applied.
        self.src.symlink('/usr/bin', '/bin')

        self.src.write_file('/bin/bla', 0o644, 'bla')

        copy_filelist(self.src, ['/bin/bla'], self.dst)

        # We should now have the same content from /SRC/usr/bin/bla in
        # /DST/usr/bin/bla
        self.assertEqual(self.src.read_file('/usr/bin/bla'),
                         self.dst.read_file('/usr/bin/bla'))

    def test_usrmerge_rel(self):

        self.src.mkdir_p('/usr/bin')

        # create a proper relative path, that should
        # work fine from inside.
        self.src.symlink('usr/bin', '/bin')

        self.src.write_file('/bin/bla', 0o644, 'bla')

        copy_filelist(self.src, ['/bin/bla'], self.dst)

        # We should now have the same content from /SRC/usr/bin/bla in
        # /DST/usr/bin/bla
        self.assertEqual(self.src.read_file('/usr/bin/bla'),
                         self.dst.read_file('/usr/bin/bla'))

    def test_deeplinks(self):

        self.src.mkdir_p('/a/b/c')

        # c <- /a/b/d
        self.src.symlink('c', '/a/b/d')

        # This write into /a/b/c/bla (c instead of d)
        self.src.write_file('/a/b/d/bla', 0o644, 'bla')

        copy_filelist(self.src, ['/a/b/d/bla'], self.dst)

        # We should now have the same content from /SRC/a/b/c/bla in
        # /DST/a/b/c/bla
        self.assertEqual(self.src.read_file('/a/b/c//bla'),
                         self.dst.read_file('/a/b/c/bla'))

    def test_multilinks(self):

        self.src.mkdir_p('/a')

        # a <- b
        # ../b <- /a/c
        self.src.symlink('a', '/b')
        self.src.symlink('../b', '/a/c')

        # This write into /a/bla
        self.src.write_file('a/c/bla', 0o644, 'bla')

        copy_filelist(self.src, ['/a/c/bla'], self.dst)

        # We should now have the content from /SRC/a/bla in /DST/a/bla
        self.assertEqual(self.src.read_file('/a/bla'),
                         self.dst.read_file('/a/bla'))

    @unittest.expectedFailure
    def test_badfile(self):
        # This should throw a CommandError
        copy_filelist(self.src, ['/doesnt/exist'], self.dst)
