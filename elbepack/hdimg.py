# ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (c) 2014-2015, 2017 Torben Hohn <torben.hohn@linutronix.de>
# Copyright (c) 2014, 2016-2017 Manuel Traut <manut@linutronix.de>
# Copyright (c) 2016, 2018 John Ogness <john.ogness@linutronix.de>
# Copyright (c) 2016 Philipp Rosenberger <p.rosenberger@linutronix.de>
# Copyright (c) 2018 Martin Kaistra <martin.kaistra@linutronix.de>
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import print_function

import os

import parted
import _ped

from elbepack.fstab import fstabentry, mountpoint_dict
from elbepack.filesystem import Filesystem, size_to_int
from elbepack.shellhelper import do, CommandError, chroot


def mkfs_mtd(mtd, fslabel, target):

    # generated files
    img_files = []

    if not mtd.has("ubivg"):
        return img_files

    ubivg = mtd.node("ubivg")
    for v in ubivg:
        if not v.tag == "ubi":
            continue

        if v.has("empty"):
            continue

        if v.has("binary"):
            continue

        label = v.text("label")
        if label not in fslabel:
            continue

        try:
            cmd = "mkfs.ubifs -r %s -o %s.ubifs -m %s -e %s -c %s %s" % (
                os.path.join(target, "filesystems", fslabel[label].id),
                os.path.join(target, label),
                ubivg.text("miniosize"),
                ubivg.text("logicaleraseblocksize"),
                ubivg.text("maxlogicaleraseblockcount"),
                fslabel[label].mkfsopt
            )
            do(cmd)
            # only append the ubifs file if creation didn't fail
            img_files.append("%s.ubifs" % label)
        except CommandError:
            # continue creating further ubifs filesystems
            pass

    return img_files


def build_image_mtd(mtd, target):

    # pylint: disable=too-many-branches

    img_files = []

    if not mtd.has("ubivg"):
        return img_files

    ubivg = mtd.node("ubivg")

    cfgfilename = "%s_%s.cfg" % (
        mtd.text("name"), mtd.node("ubivg").text("label"))
    fp = open(os.path.join(target, cfgfilename), "w")

    for vol in mtd.node("ubivg"):
        if vol.has("label"):
            fp.write("[%s]\n" % vol.text("label"))
            fp.write("mode=ubi\n")
            if not vol.has("empty"):
                if vol.has("binary"):
                    tmp = ""
                    # copy from buildenv if path starts with /
                    if vol.text("binary")[0] == '/':
                        tmp = target + "/" + "chroot" + vol.text("binary")
                    # copy from project directory
                    else:
                        tmp = target + "/" + vol.text("binary")
                    do("cp %s %s/%s.ubibin" %
                       (tmp, target, vol.text("label")))
                    img_files.append(vol.text("label") + ".ubibin")
                    fp.write(
                        "image=%s.ubibin\n" %
                        os.path.join(
                            target,
                            vol.text("label")))
                else:
                    fp.write(
                        "image=%s.ubifs\n" %
                        os.path.join(
                            target,
                            vol.text("label")))
            else:
                empt = open("/tmp/empty", "w")
                empt.write("EMPTY")
                empt.close()
                fp.write("image=/tmp/empty\n")

            fp.write("vol_type=%s\n" % vol.text("type"))
            fp.write("vol_id=%s\n" % vol.text("id"))
            fp.write("vol_name=%s\n" % vol.text("label"))

            if vol.text("size") != "remain":
                fp.write("vol_size=%d\n" % size_to_int(vol.text("size")))
            else:
                fp.write("vol_flags=autoresize\n")

    fp.close()

    if ubivg.has("subpagesize"):
        subp = "-s " + ubivg.text("subpagesize")
    else:
        subp = ""

    try:
        do("ubinize %s -o %s -p %s -m %s %s/%s_%s.cfg" %
           (subp,
            os.path.join(target, mtd.text("name")),
            ubivg.text("physicaleraseblocksize"),
            ubivg.text("miniosize"),
            target,
            mtd.text("name"),
            ubivg.text("label")))
        # only add file to list if ubinize command was successful
        img_files.append(mtd.text("name"))

    except CommandError:
        # continue with generating further images
        pass

    return img_files


class grubinstaller_base(object):
    def __init__(self, fw_type=None):
        self.fs = mountpoint_dict()
        self.fw_type = fw_type if fw_type else []

    def add_fs_entry(self, entry):
        self.fs[entry.mountpoint] = entry

    def install(self, target):
        pass


class grubinstaller202(grubinstaller_base):

    def install(self, target):
        if '/' not in self.fs:
            return

        imagemnt = os.path.join(target, "imagemnt")
        imagemntfs = Filesystem(imagemnt)
        try:
            do('cp -a /dev/loop0 /dev/poop0')

            do('losetup /dev/poop0 "%s"' % self.fs['/'].filename)
            do('kpartx -as /dev/poop0')

            for entry in self.fs.depthlist():
                do('mount /dev/mapper/poop0p%d %s' %
                   (entry.partnum, imagemntfs.fname(entry.mountpoint)))

            do("mount --bind /dev %s" % imagemntfs.fname("dev"))
            do("mount --bind /proc %s" % imagemntfs.fname("proc"))
            do("mount --bind /sys %s" % imagemntfs.fname("sys"))

            do('mkdir -p "%s"' % imagemntfs.fname("boot/grub"))

            devmap = open(imagemntfs.fname("boot/grub/device.map"), "w")
            devmap.write("(hd0) /dev/poop0\n")
            devmap.close()

            chroot(imagemnt, "update-initramfs -u -k all")
            chroot(imagemnt, "update-grub2")

            if "efi" in self.fw_type:
                grub_tgt = next(t for t in self.fw_type if t.endswith("-efi"))
                do("chroot %s grub-install --target=%s --removable "
                   "--no-floppy /dev/poop0" %
                   (imagemnt, grub_tgt))
            if "shimfix" in self.fw_type:
                # grub-install is heavily dependent on the running system having
                # a BIOS or EFI.  The initvm is BIOS-based, so fix the resulting
                # shim installation.
                do("chroot %s  /bin/bash -c '"
                   "cp -r /boot/efi/EFI/BOOT /boot/efi/EFI/debian && "
                   "cd /usr/lib/shim && f=( shim*.efi.signed ) && cp "
                   "${f[0]} /boot/efi/EFI/debian/${f[0]%%.signed}'"  %
                   imagemnt)
            if not self.fw_type or "bios" in self.fw_type:
                do("chroot %s grub-install --no-floppy /dev/poop0" %
                   (imagemnt))

        finally:
            os.unlink(imagemntfs.fname("boot/grub/device.map"))
            do("umount %s" % imagemntfs.fname("dev"), allow_fail=True)
            do("umount %s" % imagemntfs.fname("proc"), allow_fail=True)
            do("umount %s" % imagemntfs.fname("sys"), allow_fail=True)

            for entry in reversed(self.fs.depthlist()):
                do('umount /dev/mapper/poop0p%d' % entry.partnum,
                   allow_fail=True)

            do('kpartx -d /dev/poop0', allow_fail=True)
            do("losetup -d /dev/poop0", allow_fail=True)


class simple_fstype(object):
    def __init__(self, typ):
        self.type = typ


def create_partition(
        disk,
        part,
        ptype,
        fslabel,
        size_in_sectors,
        current_sector):

    # pylint: disable=too-many-arguments

    sector_size = 512
    if part.text("size") == "remain" and disk.type == "gpt":
        sz = size_in_sectors - 35 - current_sector
    elif part.text("size") == "remain":
        sz = size_in_sectors - current_sector
    else:
        sz = size_to_int(part.text("size")) / sector_size

    g = parted.Geometry(device=disk.device, start=current_sector, length=sz)
    if ptype != parted.PARTITION_EXTENDED and \
       part.text("label") in fslabel and \
       fslabel[part.text("label")].fstype == "vfat":

        fs = simple_fstype("fat32")
        ppart = parted.Partition(disk, ptype, fs, geometry=g)
        if disk.type != "gpt":
            ppart.setFlag(_ped.PARTITION_LBA)
    else:
        ppart = parted.Partition(disk, ptype, geometry=g)

    cons = parted.Constraint(exactGeom=g)
    disk.addPartition(ppart, cons)

    if part.has("bootable"):
        ppart.setFlag(_ped.PARTITION_BOOT)

    if part.has("biosgrub"):
        ppart.setFlag(_ped.PARTITION_BIOS_GRUB)

    return ppart


def create_label(disk, part, ppart, fslabel, target, grub):

    # pylint: disable=too-many-arguments

    entry = fslabel[part.text("label")]
    entry.set_geometry(ppart, disk)

    grub.add_fs_entry(entry)

    entry.losetup("loop0")
    do('mkfs.%s %s %s /dev/loop0' %
       (entry.fstype,
        entry.mkfsopt,
        entry.get_label_opt()))

    do('mount /dev/loop0 %s' % os.path.join(target, "imagemnt"))
    do('cp -a "%s/." "%s/"' %
       (os.path.join(target, "filesystems", entry.id),
        os.path.join(target, "imagemnt")),
       allow_fail=True)
    entry.tuning("/dev/loop0")
    do('umount /dev/loop0')
    do('losetup -d /dev/loop0')

    return ppart


def create_logical_partitions(disk,
                              extended,
                              epart,
                              fslabel,
                              target,
                              grub):

    # pylint: disable=too-many-arguments

    current_sector = epart.geometry.start
    size_in_sectors = current_sector + epart.geometry.length

    for logical in extended:
        if logical.tag != "logical":
            continue

        current_sector += 2048
        lpart = create_partition(
            disk,
            logical,
            parted.PARTITION_LOGICAL,
            fslabel,
            size_in_sectors,
            current_sector)
        if logical.has("label") and logical.text("label") in fslabel:
            create_label(disk, logical, lpart, fslabel, target, grub)

        current_sector += lpart.getLength()


def do_image_hd(hd, fslabel, target, grub_version, grub_fw_type=None):

    # pylint: disable=too-many-arguments
    # pylint: disable=too-many-locals
    # pylint: disable=too-many-branches

    sector_size = 512
    s = size_to_int(hd.text("size"))
    size_in_sectors = s / sector_size

    imagename = os.path.join(target, hd.text("name"))
    do('rm -f "%s"' % imagename, allow_fail=True)
    f = open(imagename, "wb")
    f.truncate(size_in_sectors * sector_size)
    f.close()

    imag = parted.Device(imagename)
    if hd.tag == "gpthd":
        disk = parted.freshDisk(imag, "gpt")
    else:
        disk = parted.freshDisk(imag, "msdos")

    if grub_version == 202:
        grub = grubinstaller202(grub_fw_type)
    else:
        grub = grubinstaller_base()

    current_sector = 2048
    for part in hd:

        if part.tag == "partition":
            ppart = create_partition(
                disk,
                part,
                parted.PARTITION_NORMAL,
                fslabel,
                size_in_sectors,
                current_sector)
            if part.text("label") in fslabel:
                create_label(disk, part, ppart, fslabel, target, grub)
        elif part.tag == "extended":
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

    if hd.has("grub-install") and grub_version:
        grub.install(target)

    return hd.text("name")


def add_binary_blob(hd, target):

    imagename = os.path.join(target, hd.text("name"))

    for binary in hd:
        if binary.tag != "binary":
            continue

        try:
            offset = binary.et.attrib["offset"]
        except KeyError:
            offset = 0

        try:
            bs = binary.et.attrib["blocksize"]
        except KeyError:
            bs = 1

        # use file from target/ dir if binary path starts with /
        if binary.et.text[0] == '/':
            bf = os.path.join(target, 'target', binary.et.text[1:])
            print(bf)
        else:
            # use file from /var/cache/elbe/<uuid> project dir
            bf = os.path.join(target, binary.et.text)

        do('dd if="%s" of="%s" seek="%s" bs="%s" conv=notrunc' %
           (bf, imagename, offset, bs))


def do_hdimg(xml, target, rfs, grub_version, grub_fw_type=None):

    # pylint: disable=too-many-arguments
    # pylint: disable=too-many-locals
    # pylint: disable=too-many-branches

    # list of created files
    img_files = []

    # Check whether we have any images first
    if not xml.tgt.has("images"):
        return img_files

    # Build a dictonary of mount points
    fslabel = {}
    mountpoints = mountpoint_dict()

    for fs in xml.tgt.node("fstab"):
        if fs.tag != "bylabel":
            continue

        # Create fstabentry Object
        e = fstabentry(xml, fs)

        # register it with mountpoints,
        # this also sets the id field
        mountpoints.register(e)

        fslabel[fs.text("label")] = e

    # Get the sorted list of mountpoints
    fslist = mountpoints.depthlist()

    # create directories, where we want our
    # filesystems later
    fspath = os.path.join(target, "filesystems")
    do('mkdir -p %s' % fspath)

    imagemnt = os.path.join(target, "imagemnt")
    do('mkdir -p %s' % imagemnt)

    # now move all mountpoints into own directories
    # begin from deepest mountpoints
    for l in reversed(fslist):
        do('mkdir -p "%s"' % os.path.join(fspath, l.id))
        do('mkdir -p "%s"' % rfs.fname('') + l.mountpoint)
        if rfs.listdir(l.mountpoint):
            do('mv "%s"/* "%s"' %
               (rfs.fname(l.mountpoint),
                os.path.join(fspath, l.id)),
               allow_fail=True)

    try:
        # Now iterate over all images and create filesystems and partitions
        for i in xml.tgt.node("images"):
            if i.tag == "msdoshd":
                img = do_image_hd(i,
                                  fslabel,
                                  target,
                                  grub_version,
                                  grub_fw_type)
                img_files.append(img)

            if i.tag == "gpthd":
                img = do_image_hd(i,
                                  fslabel,
                                  target,
                                  grub_version,
                                  grub_fw_type)
                img_files.append(img)

            if i.tag == "mtd":
                imgs = mkfs_mtd(i, fslabel, target)
                img_files.extend(imgs)
    finally:
        # Put back the filesystems into /target
        # most shallow fs first...
        for i in fslist:
            if len(os.listdir(os.path.join(fspath, i.id))) > 0:
                do('mv "%s"/* "%s"' %
                   (os.path.join(fspath, i.id), rfs.fname(i.mountpoint)),
                   allow_fail=True)

    # Files are now moved back. ubinize needs files in place, so we run it now.
    for i in xml.tgt.node("images"):
        if i.tag == "mtd":
            imgs = build_image_mtd(i, target)
            img_files.extend(imgs)

    # dd binary blobs onto images
    for i in xml.tgt.node("images"):
        if (i.tag == "msdoshd") or (i.tag == "gpthd"):
            add_binary_blob(i, target)

    # use set() to remove duplicates, but
    # return a list
    return list(set(img_files))
