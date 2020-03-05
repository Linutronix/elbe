
import unittest

from elbepack.filesystem import TmpdirFilesystem
from elbepack.efilesystem import copy_filelist

class TestCopyFilelist(unittest.TestCase):

    def setUp(self):
        self.src = TmpdirFilesystem()
        self.dst = TmpdirFilesystem()

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
