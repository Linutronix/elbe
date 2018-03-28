# ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (C) 2013  Linutronix GmbH
#
# This file is part of ELBE.
#
# ELBE is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# ELBE is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with ELBE.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import print_function

import os
from string import digits

import parted
import _ped

from elbepack.fstab import fstabentry, mountpoint_dict
from elbepack.asciidoclog import CommandError


def mkfs_mtd(outf, mtd, fslabel, rfs, target):

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
            outf.do("mkfs.ubifs -r %s -o %s.ubifs -m %s -e %s -c %s %s" % (
                os.path.join(target, "filesystems", fslabel[label].id),
                os.path.join(target, label),
                ubivg.text("miniosize"),
                ubivg.text("logicaleraseblocksize"),
                ubivg.text("maxlogicaleraseblockcount"),
                fslabel[label].mkfsopt))
            # only append the ubifs file if creation didn't fail
            img_files.append("%s.ubifs" % label)
        except CommandError as e:
            # continue creating further ubifs filesystems
            pass

    return img_files


def build_image_mtd(outf, mtd, target):

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
                    outf.do(
                        "cp %s %s/%s.ubibin" %
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
        outf.do("ubinize %s -o %s -p %s -m %s %s/%s_%s.cfg" % (
            subp,
            os.path.join(target, mtd.text("name")),
            ubivg.text("physicaleraseblocksize"),
            ubivg.text("miniosize"),
            target,
            mtd.text("name"),
            ubivg.text("label")))
        # only add file to list if ubinize command was successful
        img_files.append(mtd.text("name"))

    except CommandError as e:
        # continue with generating further images
        pass

    return img_files


def size_to_int(size):
    if size[-1] in digits:
        return int(size)

    if size.endswith("M"):
        unit = 1000 * 1000
        s = size[:-1]
    elif size.endswith("MiB"):
        unit = 1024 * 1024
        s = size[:-3]
    elif size.endswith("MB"):
        unit = 1000 * 1000
        s = size[:-2]
    if size.endswith("G"):
        unit = 1000 * 1000 * 1000
        s = size[:-1]
    elif size.endswith("GiB"):
        unit = 1024 * 1024 * 1024
        s = size[:-3]
    elif size.endswith("GB"):
        unit = 1000 * 1000 * 1000
        s = size[:-2]
    if size.endswith("k"):
        unit = 1000
        s = size[:-1]
    elif size.endswith("kiB"):
        unit = 1024
        s = size[:-3]
    elif size.endswith("kB"):
        unit = 1000
        s = size[:-2]

    return int(s) * unit


class grubinstaller_base(object):
    def __init__(self, outf, fw_type="bios"):
        self.outf = outf
        self.root = None
        self.boot = None
        self.boot_efi = None
        self.fw_type = fw_type

    def set_boot_entry(self, entry):
        print("setting boot entry")
        self.boot = entry

    def set_boot_efi_entry(self, entry):
        self.boot_efi = entry

    def set_root_entry(self, entry):
        self.root = entry

    def install(self, target):
        pass


class grubinstaller202(grubinstaller_base):

    def install(self, target):
        if not self.root:
            return

        imagemnt = os.path.join(target, "imagemnt")
        try:
            self.outf.do('cp -a /dev/loop0 /dev/poop0')

            self.outf.do('losetup /dev/poop0 "%s"' % self.root.filename)
            self.outf.do('kpartx -as /dev/poop0')
            self.outf.do(
                'mount /dev/mapper/poop0p%d %s' %
                (self.root.partnum, imagemnt))

            if self.boot:
                self.outf.do(
                    'mount /dev/mapper/poop0p%d %s' %
                    (self.boot.partnum, os.path.join(
                        imagemnt, "boot")))

            if self.boot_efi:
                self.outf.do(
                    'mount /dev/mapper/poop0p%d %s' %
                    (self.boot_efi.partnum, os.path.join(
                        imagemnt, "boot/efi")))

            self.outf.do(
                "mount --bind /dev %s" %
                os.path.join(
                    imagemnt,
                    "dev"))
            self.outf.do(
                "mount --bind /proc %s" %
                os.path.join(
                    imagemnt,
                    "proc"))
            self.outf.do(
                "mount --bind /sys %s" %
                os.path.join(
                    imagemnt,
                    "sys"))

            self.outf.do('mkdir -p "%s"' % os.path.join(imagemnt, "boot/grub"))

            devmap = open(os.path.join(imagemnt, "boot/grub/device.map"), "w")
            devmap.write("(hd0) /dev/poop0\n")
            devmap.close()

            self.outf.do("chroot %s  update-initramfs -u -k all" % imagemnt)
            self.outf.do("chroot %s  update-grub2" % imagemnt)

            if self.fw_type == "efi":
                self.outf.do(
                    "chroot %s grub-install --target=x86_64-efi --removable "
                    "--no-floppy /dev/poop0" %
                    (imagemnt))
            else:
                self.outf.do(
                    "chroot %s grub-install --no-floppy /dev/poop0" %
                    (imagemnt))

        finally:
            os.unlink(os.path.join(imagemnt, "boot/grub/device.map"))
            self.outf.do(
                "umount %s" %
                os.path.join(
                    imagemnt,
                    "dev"),
                allow_fail=True)
            self.outf.do(
                "umount %s" %
                os.path.join(
                    imagemnt,
                    "proc"),
                allow_fail=True)
            self.outf.do(
                "umount %s" %
                os.path.join(
                    imagemnt,
                    "sys"),
                allow_fail=True)

            if self.boot_efi:
                self.outf.do(
                    'umount /dev/mapper/poop0p%d' %
                    self.boot_efi.partnum, allow_fail=True)

            if self.boot:
                self.outf.do(
                    'umount /dev/mapper/poop0p%d' %
                    self.boot.partnum, allow_fail=True)

            self.outf.do(
                'umount /dev/mapper/poop0p%d' %
                self.root.partnum, allow_fail=True)

            self.outf.do('kpartx -d /dev/poop0', allow_fail=True)
            self.outf.do("losetup -d /dev/poop0", allow_fail=True)


class grubinstaller199(grubinstaller_base):

    def install(self, target):
        if not self.root:
            return

        imagemnt = os.path.join(target, "imagemnt")
        try:
            self.outf.do('cp -a /dev/loop0 /dev/poop0')
            self.outf.do('cp -a /dev/loop1 /dev/poop1')
            self.outf.do('cp -a /dev/loop2 /dev/poop2')

            self.outf.do('losetup /dev/poop0 "%s"' % self.root.filename)
            self.root.losetup(self.outf, "poop1")
            self.outf.do('mount /dev/poop1 %s' % imagemnt)

            if self.boot:
                self.boot.losetup(self.outf, "poop2")
                self.outf.do('mount /dev/poop2 %s' %
                             (os.path.join(imagemnt, "boot")))

            devmap = open(os.path.join(imagemnt, "boot/grub/device.map"), "w")
            devmap.write("(hd0) /dev/poop0\n")
            devmap.write("(hd0,%s) /dev/poop1\n" % self.root.number)
            if self.boot:
                devmap.write("(hd0,%s) /dev/poop2\n" % self.boot.number)

            devmap.close()

            self.outf.do(
                "mount --bind /dev %s" %
                os.path.join(
                    imagemnt,
                    "dev"))
            self.outf.do(
                "mount --bind /proc %s" %
                os.path.join(
                    imagemnt,
                    "proc"))
            self.outf.do(
                "mount --bind /sys %s" %
                os.path.join(
                    imagemnt,
                    "sys"))

            self.outf.do("chroot %s  update-initramfs -u -k all" % imagemnt)
            self.outf.do("chroot %s  update-grub2" % imagemnt)

            self.outf.do(
                "chroot %s  grub-install --no-floppy /dev/loop0" %
                imagemnt)

        finally:
            os.unlink(os.path.join(imagemnt, "boot/grub/device.map"))

            self.outf.do(
                "umount -l %s" %
                os.path.join(
                    imagemnt,
                    "dev"),
                allow_fail=True)
            self.outf.do(
                "umount -l %s" %
                os.path.join(
                    imagemnt,
                    "proc"),
                allow_fail=True)
            self.outf.do(
                "umount -l %s" %
                os.path.join(
                    imagemnt,
                    "sys"),
                allow_fail=True)

            self.outf.do("losetup -d /dev/poop0", allow_fail=True)

            if self.boot:
                self.outf.do('umount /dev/poop2', allow_fail=True)
                self.outf.do('losetup -d /dev/poop2', allow_fail=True)

            self.outf.do('umount /dev/poop1', allow_fail=True)
            self.outf.do('losetup -d /dev/poop1', allow_fail=True)


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


def create_label(outf, disk, part, ppart, fslabel, target, grub):

    sector_size = 512
    partition_number = ppart.number
    entry = fslabel[part.text("label")]
    entry.offset = ppart.geometry.start * sector_size
    entry.size = ppart.getLength() * sector_size
    entry.filename = disk.device.path
    entry.partnum = partition_number
    entry.number = '{}{}'.format(disk.type, partition_number)

    if entry.mountpoint == "/":
        grub.set_root_entry(entry)
    elif entry.mountpoint == "/boot":
        grub.set_boot_entry(entry)
    elif entry.mountpoint == "/boot/efi":
        grub.set_boot_efi_entry(entry)

    entry.losetup(outf, "loop0")
    outf.do(
        'mkfs.%s %s %s /dev/loop0' %
        (entry.fstype,
         entry.mkfsopt,
         entry.get_label_opt()))

    outf.do('mount /dev/loop0 %s' % os.path.join(target, "imagemnt"))
    outf.do(
        'cp -a "%s"/* "%s"' %
        (os.path.join(
            target, "filesystems", entry.id), os.path.join(
            target, "imagemnt")), allow_fail=True)
    outf.do('umount /dev/loop0')
    outf.do('losetup -d /dev/loop0')

    return ppart


def create_logical_partitions(
        outf,
        disk,
        extended,
        epart,
        fslabel,
        target,
        grub):

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
            create_label(outf, disk, logical, lpart, fslabel, target, grub)

        current_sector += lpart.getLength()


def do_image_hd(outf, hd, fslabel, target, grub_version, grub_fw_type):

    sector_size = 512
    s = size_to_int(hd.text("size"))
    size_in_sectors = s / sector_size

    imagename = os.path.join(target, hd.text("name"))
    outf.do('rm -f "%s"' % imagename, allow_fail=True)
    f = open(imagename, "wb")
    f.truncate(size_in_sectors * sector_size)
    f.close()

    imag = parted.Device(imagename)
    if hd.tag == "gpthd":
        disk = parted.freshDisk(imag, "gpt")
    else:
        disk = parted.freshDisk(imag, "msdos")

    if grub_version == 199:
        grub = grubinstaller199(outf)
    elif grub_version == 202 and grub_fw_type == "efi":
        grub = grubinstaller202(outf, "efi")
    elif grub_version == 202:
        grub = grubinstaller202(outf)
    else:
        grub = grubinstaller_base(outf)

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
                create_label(outf, disk, part, ppart, fslabel, target, grub)
        elif part.tag == "extended":
            ppart = create_partition(
                disk,
                part,
                parted.PARTITION_EXTENDED,
                fslabel,
                size_in_sectors,
                current_sector)
            create_logical_partitions(
                outf, disk, part, ppart, fslabel, target, grub)
        else:
            continue

        current_sector += ppart.getLength()

    disk.commit()

    if hd.has("grub-install") and grub_version:
        grub.install(target)

    return hd.text("name")


def add_binary_blob(outf, hd, target):

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
        if (binary.et.text[0] == '/'):
            bf = os.path.join(target, 'target', binary.et.text[1:])
            print(bf)
        # else use file from /var/cache/elbe/<uuid> project dir
        else:
            bf = os.path.join(target, binary.et.text)

        outf.do('dd if="%s" of="%s" seek="%s" bs="%s" conv=notrunc' % (
            bf,
            imagename,
            offset,
            bs))


def do_hdimg(outf, xml, target, rfs, grub_version, grub_fw_type):
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
    outf.do('mkdir -p %s' % fspath)

    imagemnt = os.path.join(target, "imagemnt")
    outf.do('mkdir -p %s' % imagemnt)

    # now move all mountpoints into own directories
    # begin from deepest mountpoints
    for l in reversed(fslist):
        outf.do('mkdir -p "%s"' % os.path.join(fspath, l.id))
        outf.do('mkdir -p "%s"' % rfs.fname('') + l.mountpoint)
        if len(rfs.listdir(l.mountpoint)) > 0:
            outf.do('mv "%s"/* "%s"' % (rfs.fname(l.mountpoint), os.path.join(
                fspath, l.id)), allow_fail=True)

    try:
        # Now iterate over all images and create filesystems and partitions
        for i in xml.tgt.node("images"):
            if i.tag == "msdoshd":
                img = do_image_hd(
                    outf,
                    i,
                    fslabel,
                    target,
                    grub_version,
                    grub_fw_type)
                img_files.append(img)

            if i.tag == "gpthd":
                img = do_image_hd(
                    outf,
                    i,
                    fslabel,
                    target,
                    grub_version,
                    grub_fw_type)
                img_files.append(img)

            if i.tag == "mtd":
                imgs = mkfs_mtd(outf, i, fslabel, rfs, target)
                img_files.extend(imgs)
    finally:
        # Put back the filesystems into /target
        # most shallow fs first...
        for i in fslist:
            if len(os.listdir(os.path.join(fspath, i.id))) > 0:
                outf.do(
                    'mv "%s"/* "%s"' %
                    (os.path.join(
                        fspath, i.id), rfs.fname(
                        i.mountpoint)), allow_fail=True)

    # Files are now moved back. ubinize needs files in place, so we run it now.
    for i in xml.tgt.node("images"):
        if i.tag == "mtd":
            imgs = build_image_mtd(outf, i, target)
            img_files.extend(imgs)

    # dd binary blobs onto images
    for i in xml.tgt.node("images"):
        if (i.tag == "msdoshd") or (i.tag == "gpt"):
            add_binary_blob(outf, i, target)

    gz_img_files = []
    for i in set(img_files):
        try:
            outf.do('gzip -f "%s"' % os.path.join(target, i))
            # only add gz to gz_img_files, if no exception is thrown
            gz_img_files.append(i + ".gz")
        except CommandError:
            pass

    return gz_img_files
