# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2014-2018 Linutronix GmbH

import contextlib
import glob
import logging
import os
import pathlib
import shlex
import subprocess
from pathlib import Path

import parted

from elbepack.filesystem import Filesystem, size_to_int
from elbepack.fstab import fstabentry, hdpart, mountpoint_dict
from elbepack.imgutils import dd, losetup, mount
from elbepack.shellhelper import chroot, do


def mkfs_mtd(mtd, fslabel, target):

    # generated files
    img_files = []

    if not mtd.has('ubivg'):
        return img_files

    ubivg = mtd.node('ubivg')
    for v in ubivg:
        if not v.tag == 'ubi':
            continue

        if v.has('empty'):
            continue

        if v.has('binary'):
            continue

        label = v.text('label')
        if label not in fslabel:
            continue

        try:
            do(['mkfs.ubifs',
                '-r', os.path.join(target, 'filesystems', fslabel[label].id),
                '-o', os.path.join(target, label) + '.ubifs',
                '-m', ubivg.text('miniosize'),
                '-e', ubivg.text('logicaleraseblocksize'),
                '-c', ubivg.text('maxlogicaleraseblockcount'),
                *fslabel[label].mkfsopts])
            # only append the ubifs file if creation didn't fail
            img_files.append(f'{label}.ubifs')
        except subprocess.CalledProcessError as e:
            logging.error('mkfs.ubifs failed: %s', e, exc_info=e)

    return img_files


def _glob_single(*args, **kwargs):
    matches = glob.glob(*args, **kwargs)
    if not matches:
        raise ValueError('no match', args)
    elif len(matches) != 1:
        raise ValueError('not exactly one match', matches, args)

    return matches[0]


def build_image_mtd(mtd, target):

    img_files = []

    if not mtd.has('ubivg'):
        return img_files

    ubivg = mtd.node('ubivg')

    cfgfilename = f"{mtd.text('name')}_{mtd.node('ubivg').text('label')}.cfg"
    fp = open(os.path.join(target, cfgfilename), 'w')

    for vol in mtd.node('ubivg'):
        if vol.has('label'):
            fp.write(f"[{vol.text('label')}]\n")
            fp.write('mode=ubi\n')
            if not vol.has('empty'):
                if vol.has('binary'):
                    tmp = ''
                    # copy from buildenv if path starts with /
                    if vol.text('binary')[0] == '/':
                        tmp = target + '/' + 'chroot' + vol.text('binary')
                    # copy from project directory
                    else:
                        tmp = target + '/' + vol.text('binary')
                    tmp = _glob_single(tmp)
                    do(['cp', tmp, target + '/' + vol.text('label') + '.ubibin'])
                    img_files.append(vol.text('label') + '.ubibin')
                    fp.write(
                        f"image={os.path.join(target, vol.text('label'))}.ubibin\n")
                else:
                    fp.write(
                        f"image={os.path.join(target, vol.text('label'))}.ubifs\n")
            else:
                empt = open('/tmp/empty', 'w')
                empt.write('EMPTY')
                empt.close()
                fp.write('image=/tmp/empty\n')

            fp.write(f"vol_type={vol.text('type')}\n")
            fp.write(f"vol_id={vol.text('id')}\n")
            fp.write(f"vol_name={vol.text('label')}\n")

            if vol.text('size') != 'remain':
                fp.write(f"vol_size={size_to_int(vol.text('size'))}\n")
            else:
                fp.write('vol_flags=autoresize\n')

    fp.close()

    if ubivg.has('subpagesize'):
        subp = ['-s', ubivg.text('subpagesize')]
    else:
        subp = []

    try:
        do(['ubinize', *subp,
            '-o', os.path.join(target, mtd.text('name')),
            '-p', ubivg.text('physicaleraseblocksize'),
            '-m', ubivg.text('miniosize'),
            f"{target}/{mtd.text('name')}_{ubivg.text('label')}.cfg"])
        # only add file to list if ubinize command was successful
        img_files.append(mtd.text('name'))

    except subprocess.CalledProcessError as e:
        logging.error('ubinize failed: %s', e, exc_info=e)

    return img_files


class grubinstaller_base:
    def __init__(self, fw_type=None):
        self.fs = mountpoint_dict()
        self.fw_type = fw_type if fw_type else []

    def add_fs_entry(self, entry):
        self.fs[entry.mountpoint] = entry

    def install(self, target, user_args):
        pass


class grubinstaller202(grubinstaller_base):

    def install(self, target, user_args):
        if '/' not in self.fs:
            return

        imagemnt = os.path.join(target, 'imagemnt')
        imagemntfs = Filesystem(imagemnt)
        with contextlib.ExitStack() as stack:
            try:
                loopdev = stack.enter_context(losetup(self.fs['/'].filename))

                for entry in self.fs.depthlist():
                    stack.enter_context(
                        mount(f'{loopdev}p{entry.partnum}',
                              imagemntfs.fname(entry.mountpoint),
                              options=entry.options))

                for bindmnt in ['/dev', '/proc', '/sys']:
                    stack.enter_context(
                        mount(bindmnt, imagemntfs.fname(bindmnt), bind=True))

                imagemntfs.mkdir_p('boot/grub')
                imagemntfs.write_file('boot/grub/device.map', 0o644, f'(hd0) {loopdev}\n')
                stack.callback(imagemntfs.remove, 'boot/grub/device.map')

                chroot(imagemnt, ['update-grub2'])

                if 'efi' in self.fw_type:
                    grub_tgt = next(t for t in self.fw_type if t.endswith('-efi'))
                    chroot(imagemnt, ['grub-install', *user_args, '--target', grub_tgt,
                                      '--removable', '--no-floppy', loopdev])
                if 'shimfix' in self.fw_type:
                    # grub-install is heavily dependent on the running system having
                    # a BIOS or EFI.  The initvm is BIOS-based, so fix the resulting
                    # shim installation.
                    chroot(imagemnt, ['cp', '-r', '/boot/efi/EFI/BOOT', '/boot/efi/EFI/debian'])
                    shim_dir = pathlib.Path(imagemnt, 'usr', 'lib', 'shim')
                    signed = next(shim_dir.glob('shim*.efi.signed'))
                    do(['cp', signed, imagemnt + '/boot/efi/EFI/debian/' + signed.stem])
                if not self.fw_type or 'bios' in self.fw_type:
                    chroot(imagemnt, ['grub-install', *user_args, '--target', 'i386-pc',
                                      '--no-floppy', loopdev])

            except subprocess.CalledProcessError as E:
                logging.error('Fail installing grub device: %s', E)


class grubinstaller97(grubinstaller_base):

    def install(self, target, user_args):
        if '/' not in self.fs:
            return

        imagemnt = os.path.join(target, 'imagemnt')
        imagemntfs = Filesystem(imagemnt)
        with contextlib.ExitStack() as stack:
            try:
                loopdev = stack.enter_context(losetup(self.fs['/'].filename))

                bootentry = 0

                for entry in self.fs.depthlist():
                    if entry.mountpoint.startswith('/boot'):
                        bootentry_label = entry.label
                        bootentry = int(entry.partnum)
                    stack.enter_context(
                        mount(f'{loopdev}p{entry.partnum}',
                              imagemntfs.fname(entry.mountpoint),
                              options=entry.options))

                if not bootentry:
                    bootentry_label = entry.label
                    bootentry = int(entry.partnum)

                for bindmnt in ['/dev', '/proc', '/sys']:
                    stack.enter_context(
                        mount(bindmnt, imagemntfs.fname(bindmnt), bind=True))

                imagemntfs.mkdir_p('boot/grub')
                imagemntfs.write_file('boot/grub/device.map', 0o644, f'(hd0) {loopdev}\n')
                stack.callback(imagemntfs.remove, 'boot/grub/device.map')

                # Replace groot and kopt because else they will be given
                # bad values
                chroot(imagemnt, ['sed', '-in',
                                  '-e', rf's/^# groot=.*$/# groot=\(hd0,{bootentry - 1}\)/',
                                  '-e', rf's/^# kopt=.*$/# kopt=root=LABEL={bootentry_label}/',
                                  '/boot/grub/menu.lst'])

                chroot(imagemnt, ['update-grub'])

                chroot(imagemnt, ['grub-install', *user_args, '--no-floppy', loopdev])

            except subprocess.CalledProcessError as E:
                logging.error('Fail installing grub device: %s', E)


class simple_fstype:
    def __init__(self, typ):
        self.type = typ


def create_partition(
        disk,
        part,
        ptype,
        fslabel,
        size_in_sectors,
        current_sector):

    sector_size = 512
    if part.text('size') == 'remain' and disk.type == 'gpt':
        sz = size_in_sectors - 35 - current_sector
    elif part.text('size') == 'remain':
        sz = size_in_sectors - current_sector
    else:
        sz = size_to_int(part.text('size')) // sector_size

    g = parted.Geometry(device=disk.device, start=current_sector, length=sz)
    if ptype != parted.PARTITION_EXTENDED and \
       part.text('label') in fslabel and \
       fslabel[part.text('label')].fstype == 'vfat':

        fs = simple_fstype('fat32')
        ppart = parted.Partition(disk, ptype, fs, geometry=g)
        if disk.type != 'gpt':
            ppart.setFlag(parted.PARTITION_LBA)
    else:
        ppart = parted.Partition(disk, ptype, geometry=g)

    if disk.type == 'gpt' and part.has('name'):
        ppart.set_name(part.text('name'))

    cons = parted.Constraint(exactGeom=g)
    disk.addPartition(ppart, cons)

    if part.has('bootable'):
        ppart.setFlag(parted.PARTITION_BOOT)

    if part.has('biosgrub'):
        ppart.setFlag(parted.PARTITION_BIOS_GRUB)

    return ppart


def create_label(disk, part, ppart, fslabel, target, grub):

    entry = fslabel[part.text('label')]
    entry.set_geometry(ppart, disk)

    grub.add_fs_entry(entry)

    with entry.losetup() as loopdev:
        do(
            f'mkfs.{entry.fstype} {" ".join(entry.mkfsopts)} {entry.get_label_opt()} '
            f'{loopdev}')

        _execute_fs_commands(entry.fs_device_commands, dict(device=loopdev))

        mount_path = Path(target, 'imagemnt')

        with mount(loopdev, mount_path, options=entry.options):
            _execute_fs_commands(entry.fs_path_commands, dict(path=mount_path))
            do([
                'cp', '-a',
                os.path.join(target, 'filesystems', entry.id) + '/.',
                str(mount_path) + '/',
            ])

    return ppart


def _execute_fs_commands(commands, replacements):
    for command in commands:
        try:
            do(command.format(**replacements))
        except KeyError as E:
            logging.error('Filesystem finetuning command failed: invalid key "%s"', E)
        except Exception as E:
            logging.error('Filesystem finetuning command failed: %s', E)


def create_binary(disk, part, ppart, target):

    entry = hdpart()
    entry.set_geometry(ppart, disk)

    with entry.losetup() as loopdev:
        # copy from buildenv if path starts with /
        if part.text('binary')[0] == '/':
            tmp = target + '/' + 'chroot' + part.text('binary')
        # copy from project directory
        else:
            tmp = target + '/' + part.text('binary')

        tmp = _glob_single(tmp)
        dd({'if': tmp, 'of': loopdev})


def create_logical_partitions(disk,
                              extended,
                              epart,
                              fslabel,
                              target,
                              grub):

    current_sector = epart.geometry.start
    size_in_sectors = current_sector + epart.geometry.length

    for logical in extended:
        if logical.tag != 'logical':
            continue

        current_sector += 2048
        lpart = create_partition(
            disk,
            logical,
            parted.PARTITION_LOGICAL,
            fslabel,
            size_in_sectors,
            current_sector)
        if logical.has('binary'):
            create_binary(disk, logical, lpart, target)
        elif logical.has('label') and logical.text('label') in fslabel:
            create_label(disk, logical, lpart, fslabel, target, grub)

        current_sector += lpart.getLength()


def do_image_hd(hd, fslabel, target, grub_version, grub_fw_type=None):

    sector_size = 512
    s = size_to_int(hd.text('size'))
    size_in_sectors = s // sector_size

    imagename = os.path.join(target, hd.text('name'))
    do(['rm', '-f', imagename], check=False)
    f = open(imagename, 'wb')
    f.truncate(size_in_sectors * sector_size)
    f.close()

    imag = parted.Device(imagename)
    if hd.tag == 'gpthd':
        disk = parted.freshDisk(imag, 'gpt')
    else:
        disk = parted.freshDisk(imag, 'msdos')

    if grub_version == 202:
        grub = grubinstaller202(grub_fw_type)
    elif grub_version == 97:
        grub = grubinstaller97(grub_fw_type)
    else:
        grub = grubinstaller_base()

    current_sector = size_to_int(hd.text('first_partition_sector',
                                         default='2048'))

    for part in hd:

        if part.tag == 'partition':
            ppart = create_partition(
                disk,
                part,
                parted.PARTITION_NORMAL,
                fslabel,
                size_in_sectors,
                current_sector)
            if part.has('binary'):
                create_binary(disk, part, ppart, target)
            elif part.text('label') in fslabel:
                create_label(disk, part, ppart, fslabel, target, grub)
        elif part.tag == 'extended':
            ppart = create_partition(
                disk,
                part,
                parted.PARTITION_EXTENDED,
                fslabel,
                size_in_sectors,
                current_sector)
            create_logical_partitions(disk, part, ppart,
                                      fslabel, target, grub)
        else:
            continue

        current_sector += ppart.getLength()

    disk.commit()

    if hd.has('grub-install') and grub_version:
        grub.install(target, shlex.split(hd.text('grub-install')))

    return hd.text('name')


def add_binary_blob(hd, target):

    imagename = os.path.join(target, hd.text('name'))

    for binary in hd:
        if binary.tag != 'binary':
            continue

        try:
            offset = binary.et.attrib['offset']
        except KeyError:
            offset = 0

        try:
            bs = binary.et.attrib['blocksize']
        except KeyError:
            bs = 1

        # use file from target/ dir if binary path starts with /
        if binary.et.text[0] == '/':
            bf = os.path.join(target, 'target', binary.et.text[1:])
            print(bf)
        else:
            # use file from /var/cache/elbe/<uuid> project dir
            bf = os.path.join(target, binary.et.text)

        dd({'if': bf, 'of': imagename, 'seek': offset, 'bs': bs, 'conv': 'notrunc'})


def do_hdimg(xml, target, rfs, grub_version, grub_fw_type=None):

    # list of created files
    img_files = []

    # Check whether we have any images first
    if not xml.tgt.has('images'):
        return img_files

    # Build a dictonary of mount points
    fslabel = {}
    mountpoints = mountpoint_dict()

    for fs in xml.tgt.node('fstab'):
        if fs.tag != 'bylabel':
            continue

        # Create fstabentry Object
        e = fstabentry(xml, fs)

        # register it with mountpoints,
        # this also sets the id field
        mountpoints.register(e)

        fslabel[fs.text('label')] = e

    # Get the sorted list of mountpoints
    fslist = mountpoints.depthlist()

    # create directories, where we want our
    # filesystems later
    fspath = os.path.join(target, 'filesystems')
    do(['mkdir', '-p', fspath])

    imagemnt = os.path.join(target, 'imagemnt')
    do(['mkdir', '-p', imagemnt])

    # now move all mountpoints into own directories
    # begin from deepest mountpoints
    for lic in reversed(fslist):
        do(['mkdir', '-p', os.path.join(fspath, lic.id)])
        do(['mkdir', '-p', rfs.fname(lic.mountpoint)])
        if rfs.listdir(lic.mountpoint):
            do(
               f'mv "{rfs.fname(lic.mountpoint)}"/* '
               f'"{os.path.join(fspath, lic.id)}"',
               check=False)

    try:
        # Now iterate over all images and create filesystems and partitions
        for i in xml.tgt.node('images'):
            if i.tag == 'msdoshd':
                img = do_image_hd(i,
                                  fslabel,
                                  target,
                                  grub_version,
                                  grub_fw_type)
                img_files.append(img)

            if i.tag == 'gpthd':
                img = do_image_hd(i,
                                  fslabel,
                                  target,
                                  grub_version,
                                  grub_fw_type)
                img_files.append(img)

            if i.tag == 'mtd':
                imgs = mkfs_mtd(i, fslabel, target)
                img_files.extend(imgs)
    finally:
        # Put back the filesystems into /target
        # most shallow fs first...
        for i in fslist:
            if len(os.listdir(os.path.join(fspath, i.id))) > 0:
                do(
                   f'mv "{os.path.join(fspath, i.id)}"/* '
                   f'"{rfs.fname(i.mountpoint)}"',
                   check=False)

    # Files are now moved back. ubinize needs files in place, so we run it now.
    for i in xml.tgt.node('images'):
        if i.tag == 'mtd':
            imgs = build_image_mtd(i, target)
            img_files.extend(imgs)

    # dd binary blobs onto images
    for i in xml.tgt.node('images'):
        if (i.tag == 'msdoshd') or (i.tag == 'gpthd'):
            add_binary_blob(i, target)

    # use set() to remove duplicates, but
    # return a list
    return list(set(img_files))
