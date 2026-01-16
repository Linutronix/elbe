# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2015-2018 Linutronix GmbH

import contextlib
import filecmp
import io
import logging
import os
import pathlib
import shutil
import subprocess
import tempfile
import time

from elbepack.filesystem import Filesystem
from elbepack.fstab import fstabentry
from elbepack.imgutils import mount
from elbepack.licencexml import copyright_xml
from elbepack.packers import default_packer
from elbepack.shellhelper import chroot, do
from elbepack.version import elbe_version


def copy_filelist(src, file_lst, dst):

    files = set()
    copied = set()

    # Make sure to copy parent directories
    #
    # For example, if file_lst = ['/usr/bin/bash'],
    # we might get {'/usr/bin', '/usr', '/usr/bin/bash'}
    for f in file_lst:
        parts = f.rstrip('\n')
        while parts != os.sep:
            files.add(parts)
            parts, _ = os.path.split(parts)

    # Start from closest to root first
    files = list(files)
    files.sort()
    files.reverse()

    while files:

        f = files.pop()
        copied.add(f)

        if src.islink(f):

            tgt = src.readlink(f)

            if not src.lexists(tgt):
                dst.symlink(tgt, f, allow_exists=True)
                continue

            # If the target is not yet in the destination RFS, we need
            # to defer the copy of the symlink after the target is
            # resolved.  Thus, we recusively call copy_filelist
            #
            # Not that this will result in an infinite loop for
            # circular symlinks
            if not dst.lexists(tgt):
                if not os.path.isabs(tgt):
                    lst = [os.path.join(os.path.dirname(f), tgt)]
                else:
                    lst = [tgt]
                copy_filelist(src, lst, dst)

            dst.symlink(tgt, f, allow_exists=True)

        elif src.isdir(f):
            if not dst.isdir(f):
                dst.mkdir(f)
            st = src.stat(f)
            dst.chown(f, st.st_uid, st.st_gid)

        else:
            try:
                shutil.copy2(src.realpath(f), dst.realpath(f))
            except OSError as E:
                logging.warning('Error while copying from %s to %s of file %s - %s',
                                src.path, dst.path, f, E)

    # update utime which will change after a file has been copied into
    # the directory
    for f in copied:
        if src.isdir(f) and not src.islink(f):
            shutil.copystat(src.fname(f), dst.fname(f))


def dpkg_architecture():
    return subprocess.check_output(
        ['dpkg', '--print-architecture'], text=True, encoding='ascii',
    ).rstrip('\n')


def _readlines(rfs, file):
    try:
        with rfs.open(file) as f:
            return f.readlines()
    except FileNotFoundError:
        return []


def extract_target(src, xml, dst, cache):

    # create filelists describing the content of the target rfs
    if xml.tgt.has('tighten') or xml.tgt.has('diet'):
        pkglist = xml.get_target_packages()
        arch = xml.text('project/buildimage/arch', key='arch')

        if xml.tgt.has('diet'):
            if xml.has('target/pkg-blacklist/'):
                blacklist = [p.et.text for p in xml.node('target/pkg-blacklist/target')]
            withdeps = []
            for p in pkglist:
                if p in blacklist:
                    continue
                deps = cache.get_dependencies(p, blacklist)
                withdeps += [d.name for d in deps]
                withdeps += [p]

            pkglist = list(set(withdeps))
        elif xml.has('target/pkg-blacklist/'):
            logging.error(
                'Impossible to blacklist packages outside of diet mode')

        file_list = []
        for line in pkglist:
            file_list += _readlines(src, f'var/lib/dpkg/info/{line}.list')
            file_list += _readlines(src, f'var/lib/dpkg/info/{line}.conffiles')

            file_list += _readlines(src, f'var/lib/dpkg/info/{line}:{arch}.list')
            file_list += _readlines(src, f'var/lib/dpkg/info/{line}:{arch}.conffiles')

        file_list = sorted(set(file_list),
                           key=lambda k: k[4:] if k.startswith('/usr') else k)
        copy_filelist(src, file_list, dst)
    else:
        # first copy most diretories
        if xml.has('target/pkg-blacklist/'):
            logging.error(
                'Impossible to blacklist packages outside of diet mode')
        for f in src.listdir():
            subprocess.call(['cp', '-a', '--reflink=auto', f, dst.fname('')])

    try:
        dst.mkdir_p('dev')
    except BaseException:
        pass
    try:
        dst.mkdir_p('proc')
    except BaseException:
        pass
    try:
        dst.mkdir_p('sys')
    except BaseException:
        pass

    if xml.tgt.has('setsel'):
        pkglist = xml.get_target_packages()
        psel = 'var/cache/elbe/pkg-selections'

        with open(dst.fname(psel), 'w+') as f:
            for item in pkglist:
                f.write(f'{item}  install\n')

        host_arch = dpkg_architecture()
        if xml.is_cross(host_arch):
            ui = '/usr/share/elbe/qemu-elbe/' + str(xml.defs['userinterpr'])
            if not os.path.exists(ui):
                ui = '/usr/bin/' + str(xml.defs['userinterpr'])
            do(f"cp {ui} {dst.fname('usr/bin')}")

        cmds = [['--clear-selections'],
                ['--set-selections', dst.fname(psel)],
                ['--purge', '-a']]
        for cmd in cmds:
            chroot(dst.path, ['/usr/bin/dpkg', *cmd])


class ElbeFilesystem(Filesystem):

    def dump_elbeversion(self, xml):
        f = self.open('etc/elbe_version', 'w+')
        f.write(f"{xml.prj.text('name')} {xml.prj.text('version')}\n")
        f.write(f'this RFS was generated by elbe {elbe_version}\n')
        f.write(time.strftime('%c\n'))
        f.close()

        version_file = self.open('etc/updated_version', 'w')
        version_file.write(xml.text('/project/version'))
        version_file.close()

        def opener(path, flags):
            return os.open(path, flags, mode=0o400)

        with self.open('etc/elbe_base.xml', 'wb', opener=opener) as elbe_base:
            xml.xml.write(elbe_base)

    def write_licenses(self, f, pkglist, xml_fname=None):
        licence_xml = copyright_xml()
        for pkg in pkglist:
            copyright_file = os.path.join('/usr/share/doc', pkg, 'copyright')
            copyright_fname = self.fname(copyright_file)
            if os.path.isfile(copyright_fname):
                try:
                    with io.open(copyright_fname, 'r',
                                 encoding='utf-8', errors='replace') as lic:
                        lic_text = lic.read()
                except IOError as e:
                    logging.exception('Error while processing license file %s',
                                      copyright_fname)
                    lic_text = u"Error while processing license file %s: '%s'" % (
                        copyright_file, e.strerror)
            else:
                logging.warning('License file does not exist, skipping %s',
                                copyright_fname)
                continue
            # in Python2 'pkg' is a binary string whereas in Python3 it is a
            # unicode string. So make sure that pkg ends up as a unicode string
            # in both Python2 and Python3.
            pkg = pkg.encode(encoding='utf-8').decode(encoding='utf-8')

            if f is not None:
                f.write(pkg)
                f.write(':\n======================================'
                        '==========================================')
                f.write('\n')
                f.write(lic_text)
                f.write('\n\n')

            if xml_fname is not None:
                licence_xml.add_copyright_file(pkg, lic_text)

        if xml_fname is not None:
            licence_xml.write(xml_fname)


def _file_or_directory_seem_equal(a, b):
    a = pathlib.Path(a)
    b = pathlib.Path(b)

    if not a.exists() and not b.exists():
        return True

    elif a.exists() != b.exists():
        return False

    elif a.is_file() and b.is_file():
        return filecmp.cmp(a, b, shallow=False)

    elif a.is_dir() and b.is_dir():
        dircmp = filecmp.dircmp(a, b, shallow=False)
        return any([
            dircmp.left_only, dircmp.right_only,
            dircmp.common_funny, dircmp.diff_files, dircmp.funny_files,
        ])

    else:
        raise ValueError(f'{a} and {b} have conflicting or unhandled types')


class Excursion:

    def __init__(self, path, restore=True, dst=None):
        self.origin = path
        self.restore = restore
        self.dst = dst or self.origin

    def do(self, rfs):
        if rfs.lexists(self.origin) and self.restore is True:
            save_to = self._saved_to()
            shutil.move(rfs.fname(self.origin), rfs.fname(save_to))
        if os.path.exists(self.origin):
            shutil.copy2(self.origin, rfs.fname(self.dst))

    def end(self, rfs):
        self._undo_excursion(rfs)
        self._del_rfs_file(self._saved_to(), rfs)

    def _saved_to(self):
        return f'{self.origin}.orig'

    # This should be a method of rfs
    @staticmethod
    def _del_rfs_file(filename, rfs):
        if rfs.lexists(filename):
            if rfs.isdir(filename):
                shutil.rmtree(rfs.fname(filename))
            else:
                os.unlink(rfs.fname(filename))

    def _undo_excursion(self, rfs):
        saved_to = self._saved_to()

        if not _file_or_directory_seem_equal(rfs.fname(self.dst), self.origin):
            # Excursed file was modified, keep the changes.
            return

        self._del_rfs_file(self.dst, rfs)
        if self.restore is True and rfs.lexists(saved_to):
            shutil.move(rfs.fname(saved_to), rfs.fname(self.dst))


class _ExcursionContext:
    def __init__(self, rfs, excursion):
        self.rfs = rfs
        self.excursion = excursion
        self._ended = False

    def __enter__(self):
        self.excursion.do(self.rfs)
        return self

    def __exit__(self, typ, value, traceback):
        self.end()

    def end(self):
        if not self._ended:
            self.excursion.end(self.rfs)
            self._ended = True


class _SimpleTmpFile:
    def __init__(self, contents, mode):
        self.contents = contents
        self.mode = mode

    def __enter__(self):
        handle, path = tempfile.mkstemp()
        self.path = pathlib.Path(path)
        self.path.write_text(self.contents)
        self.path.chmod(self.mode)

        return self.path

    def __exit__(self, typ, value, traceback):
        self.path.unlink()


class ChRootFilesystem(ElbeFilesystem):

    def __init__(self, path, interpreter=None, clean=False):
        super().__init__(path, clean)
        self.interpreter = interpreter
        self.cwd = os.open('/', os.O_RDONLY)
        self.inchroot = False

    def __del__(self):
        os.close(self.cwd)

    def __enter__(self):
        self._exitstack = contextlib.ExitStack()

        policy_rc_d = self._exitstack.enter_context(
                _SimpleTmpFile('#!/bin/sh\nexit 101\n', 0o755))

        excursions = [
            Excursion('/etc/resolv.conf'),
            Excursion('/etc/apt/apt.conf'),
            Excursion(str(policy_rc_d), dst='/usr/sbin/policy-rc.d'),
        ]

        self.mkdir_p('usr/bin')
        self.mkdir_p('usr/sbin')

        if self.interpreter:
            ui = '/usr/share/elbe/qemu-elbe/' + self.interpreter
            if not os.path.exists(ui):
                ui = '/usr/bin/' + self.interpreter

            excursions.append(Excursion(ui, False, '/usr/bin/' + self.interpreter))

        self._excursions = [
            self._exitstack.enter_context(_ExcursionContext(self, excursion))
            for excursion in excursions
        ]

        if self.path != '/':
            self._exitstack.enter_context(
                    mount(None, self.fname('/proc'), type='proc', log_output=False))
            self._exitstack.enter_context(
                    mount(None, self.fname('/sys'), type='sysfs', log_output=False))
            self._exitstack.enter_context(
                    mount('/dev', self.fname('/dev'), bind=True, log_output=False))
            self._exitstack.enter_context(
                    mount('/dev/pts', self.fname('/dev/pts'), bind=True, log_output=False))

        return self

    def __exit__(self, typ, value, traceback):
        if self.inchroot:
            self._exitstack.callback(self.leave_chroot)

        self._exitstack.__exit__(typ, value, traceback)

    def end_excursion(self, origin):
        for excursion_context in self._excursions:
            if origin == excursion_context.excursion.origin:
                excursion_context.end()
                return

    def enter_chroot(self):
        assert not self.inchroot

        os.environ['LANG'] = 'C'
        os.environ['LANGUAGE'] = 'C'
        os.environ['LC_ALL'] = 'C'

        os.chdir(self.path)
        self.inchroot = True

        if self.path == '/':
            return

        os.chroot(self.path)

    def leave_chroot(self):
        assert self.inchroot

        os.fchdir(self.cwd)

        self.inchroot = False
        if self.path == '/':
            return

        os.chroot('.')


class TargetFs(ChRootFilesystem):
    def __init__(self, path, xml, clean=True):
        super().__init__(path, xml.defs['userinterpr'], clean)
        self.xml = xml
        self.images = []
        self.image_packers = {}

    def write_fstab(self, xml):
        if not self.exists('etc'):
            if self.islink('etc'):
                self.mkdir(self.realpath('etc'))
            else:
                self.mkdir('etc')

        if xml.tgt.has('fstab'):
            f = self.open('etc/fstab', 'w')
            for fs in xml.tgt.node('fstab'):
                if not fs.has('nofstab'):
                    fstab = fstabentry(xml, fs)
                    f.write(fstab.get_str())
            f.close()

    def part_target(self, targetdir, grub_version, grub_fw_type=None):
        from elbepack.hdimg import do_hdimg

        # create target images and copy the rfs into them
        hdimages = do_hdimg(self.xml,
                            targetdir,
                            self,
                            grub_version,
                            grub_fw_type)

        for i in hdimages:
            self.images.append(i)
            self.image_packers[i] = default_packer

        if self.xml.has('target/package/tar'):
            targz_name = self.xml.text('target/package/tar/name')
            try:
                options = ''
                if self.xml.has('target/package/tar/options'):
                    options = self.xml.text('target/package/tar/options')
                cmd = 'tar cfz %(dest)s/%(fname)s -C %(sdir)s %(options)s .'
                args = dict(
                    options=options,
                    dest=targetdir,
                    fname=targz_name,
                    sdir=self.fname('')
                )
                do(cmd % args)
                # only append filename if creating tarball was successful
                self.images.append(targz_name)
            except subprocess.CalledProcessError:
                # error was logged; continue creating cpio image
                pass

        if self.xml.has('target/package/cpio'):
            oldwd = os.getcwd()
            cpio_name = self.xml.text('target/package/cpio/name')
            os.chdir(self.fname(''))
            try:
                do(
                    f'find . -print | cpio -ov -H newc >'
                    f'{os.path.join(targetdir, cpio_name)}')
                # only append filename if creating cpio was successful
                self.images.append(cpio_name)
            except subprocess.CalledProcessError:
                # error was logged; continue
                pass
            os.chdir(oldwd)

        if self.xml.has('target/package/squashfs'):
            oldwd = os.getcwd()
            sfs_name = self.xml.text('target/package/squashfs/name')
            os.chdir(self.fname(''))
            try:
                options = ''
                if self.xml.has('target/package/squashfs/options'):
                    options = self.xml.text('target/package/squashfs/options')

                do(
                    f"mksquashfs {self.fname('')} {targetdir}/{sfs_name} "
                    f'-noappend -no-progress {options}')
                # only append filename if creating mksquashfs was successful
                self.images.append(sfs_name)
            except subprocess.CalledProcessError:
                # error was logged; continue
                pass
            os.chdir(oldwd)

    def pack_images(self, builddir):
        for img, packer in self.image_packers.items():
            self.images.remove(img)
            packed = packer.pack_file(builddir, img)
            if packed:
                self.images.append(packed)
