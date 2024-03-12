# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2015-2018 Linutronix GmbH

import io
import logging
import os
import shutil
import stat
import subprocess
import time

from elbepack.filesystem import Filesystem
from elbepack.fstab import fstabentry
from elbepack.hdimg import do_hdimg
from elbepack.licencexml import copyright_xml
from elbepack.packers import default_packer
from elbepack.shellhelper import chroot, do, get_command_out, system
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
                system(
                    'cp -a --reflink=auto '
                    f'"{src.realpath(f)}" "{dst.realpath(f)}"')
            except subprocess.CalledProcessError as E:
                logging.warning('Error while copying from %s to %s of file %s - %s',
                                src.path, dst.path, f, E)

    # update utime which will change after a file has been copied into
    # the directory
    for f in copied:
        if src.isdir(f) and not src.islink(f):
            shutil.copystat(src.fname(f), dst.fname(f))


def extract_target(src, xml, dst, cache):

    # create filelists describing the content of the target rfs
    if xml.tgt.has('tighten') or xml.tgt.has('diet'):
        pkglist = [n.et.text for n in xml.node(
            'target/pkg-list') if n.tag == 'pkg']
        arch = xml.text('project/buildimage/arch', key='arch')

        if xml.tgt.has('diet'):
            withdeps = []
            for p in pkglist:
                deps = cache.get_dependencies(p)
                withdeps += [d.name for d in deps]
                withdeps += [p]

            pkglist = list(set(withdeps))

        file_list = []
        for line in pkglist:
            file_list += src.cat_file(f'var/lib/dpkg/info/{line}.list')
            file_list += src.cat_file(f'var/lib/dpkg/info/{line}.conffiles')

            file_list += src.cat_file(f'var/lib/dpkg/info/{line}:{arch}.list')
            file_list += src.cat_file(
                f'var/lib/dpkg/info/{line}:{arch}.conffiles')

        file_list = sorted(set(file_list),
                           key=lambda k: k[4:] if k.startswith('/usr') else k)
        copy_filelist(src, file_list, dst)
    else:
        # first copy most diretories
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
        pkglist = [n.et.text for n in xml.node(
            'target/pkg-list') if n.tag == 'pkg']
        psel = 'var/cache/elbe/pkg-selections'

        with open(dst.fname(psel), 'w+') as f:
            for item in pkglist:
                f.write(f'{item}  install\n')

        host_arch = get_command_out('dpkg --print-architecture').strip()
        if xml.is_cross(host_arch):
            ui = '/usr/share/elbe/qemu-elbe/' + str(xml.defs['userinterpr'])
            if not os.path.exists(ui):
                ui = '/usr/bin/' + str(xml.defs['userinterpr'])
            do(f"cp {ui} {dst.fname('usr/bin')}")

        cmds = ['--clear-selections',
                f'--set-selections < {dst.fname(psel)}',
                '--purge -a']
        for cmd in cmds:
            chroot(dst.path, f'/usr/bin/dpkg {cmd}')


class ElbeFilesystem(Filesystem):
    def __init__(self, path, clean=False):
        Filesystem.__init__(self, path, clean)

    def dump_elbeversion(self, xml):
        f = self.open('etc/elbe_version', 'w+')
        f.write(f"{xml.prj.text('name')} {xml.prj.text('version')}\n")
        f.write(f'this RFS was generated by elbe {elbe_version}\n')
        f.write(time.strftime('%c\n'))
        f.close()

        version_file = self.open('etc/updated_version', 'w')
        version_file.write(xml.text('/project/version'))
        version_file.close()

        elbe_base = self.open('etc/elbe_base.xml', 'wb')
        xml.xml.write(elbe_base)
        elbe_base.close()
        self.chmod('etc/elbe_base.xml', stat.S_IREAD)

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


class Excursion:

    RFS = {}

    @classmethod
    def begin(cls, rfs):
        cls.RFS[rfs.path] = []

    @classmethod
    def add(cls, rfs, path, restore=True, dst=None):
        cls.RFS[rfs.path].append(Excursion(path, restore, dst))

    @classmethod
    def do(cls, rfs):
        r = cls.RFS[rfs.path]
        for tmp in r:
            tmp._do_excursion(rfs)

    @classmethod
    def end(cls, rfs):
        r = cls.RFS[rfs.path]
        for tmp in r:
            if tmp.origin not in rfs.protect_from_excursion:
                tmp._undo_excursion(rfs)
            else:
                tmp._del_rfs_file(tmp._saved_to(), rfs)
        del r

    def __init__(self, path, restore, dst):
        self.origin = path
        self.restore = restore
        self.dst = dst

    def _saved_to(self):
        return f'{self.origin}.orig'

    def _do_excursion(self, rfs):
        if rfs.lexists(self.origin) and self.restore is True:
            save_to = self._saved_to()
            system(f'mv {rfs.fname(self.origin)} {rfs.fname(save_to)}')
        if os.path.exists(self.origin):
            if self.dst is not None:
                dst = self.dst
            else:
                dst = self.origin
            system(f'cp {self.origin} {rfs.fname(dst)}')

    # This should be a method of rfs
    @staticmethod
    def _del_rfs_file(filename, rfs):
        if rfs.lexists(filename):
            flags = '-f'
            if rfs.isdir(filename):
                flags += 'r'
            system(f'rm {flags} {rfs.fname(filename)}')

    def _undo_excursion(self, rfs):
        saved_to = self._saved_to()
        self._del_rfs_file(self.origin, rfs)
        if self.restore is True and rfs.lexists(saved_to):
            system(f'mv {rfs.fname(saved_to)} {rfs.fname(self.origin)}')


class ChRootFilesystem(ElbeFilesystem):

    def __init__(self, path, interpreter=None, clean=False):
        ElbeFilesystem.__init__(self, path, clean)
        self.interpreter = interpreter
        self.cwd = os.open('/', os.O_RDONLY)
        self.inchroot = False
        self.protect_from_excursion = set()

    def __del__(self):
        os.close(self.cwd)

    def __enter__(self):
        Excursion.begin(self)
        Excursion.add(self, '/etc/resolv.conf')
        Excursion.add(self, '/etc/apt/apt.conf')
        Excursion.add(self, '/usr/sbin/policy-rc.d')

        if self.interpreter:
            if not self.exists('usr/bin'):
                if self.islink('usr/bin'):
                    Excursion.add(self, '/usr/bin')

            ui = '/usr/share/elbe/qemu-elbe/' + self.interpreter
            if not os.path.exists(ui):
                ui = '/usr/bin/' + self.interpreter

            Excursion.add(self, ui, False, '/usr/bin')

        Excursion.do(self)

        self.mkdir_p('usr/bin')
        self.mkdir_p('usr/sbin')
        self.write_file('usr/sbin/policy-rc.d', 0o755, '#!/bin/sh\nexit 101\n')
        self.mount()
        return self

    def __exit__(self, _typ, _value, _traceback):
        if self.inchroot:
            self.leave_chroot()
        self.umount()

        Excursion.end(self)
        self.protect_from_excursion = set()

    def protect(self, files):
        self.protect_from_excursion = files
        return self

    def mount(self):
        if self.path == '/':
            return
        try:
            system(f'mount -t proc none {self.path}/proc')
            system(f'mount -t sysfs none {self.path}/sys')
            system(f'mount -o bind /dev {self.path}/dev')
            system(f'mount -o bind /dev/pts {self.path}/dev/pts')
        except BaseException:
            self.umount()
            raise

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

    def _umount(self, path):
        path = os.path.join(self.path, path)
        if os.path.ismount(path):
            system(f'umount {path}')

    def umount(self):
        if self.path == '/':
            return
        self._umount('proc/sys/fs/binfmt_misc')
        self._umount('proc')
        self._umount('sys')
        self._umount('dev/pts')
        time.sleep(0.5)
        self._umount('dev')

    def leave_chroot(self):
        assert self.inchroot

        os.fchdir(self.cwd)

        self.inchroot = False
        if self.path == '/':
            return

        os.chroot('.')


class TargetFs(ChRootFilesystem):
    def __init__(self, path, xml, clean=True):
        ChRootFilesystem.__init__(self, path, xml.defs['userinterpr'], clean)
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


class BuildImgFs(ChRootFilesystem):
    def __init__(self, path, interpreter):
        ChRootFilesystem.__init__(self, path, interpreter)
