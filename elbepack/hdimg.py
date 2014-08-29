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

import os
from string import digits

import parted
import _ped

from elbepack.fstab import fstabentry
from elbepack.asciidoclog import CommandError

def mkfs_mtd( outf, mtd, fslabel, rfs, target ):

    #generated files
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
            # allow_fail is set that the generation of other images is done,
            # even if this step fails
            outf.do( "cp %s %s" % ( rfs.fname( v.text("binary") ), target ),
                        allow_fail=True)
            continue

        label = v.text("label")
        if not fslabel.has_key(label):
            continue

        try:
            outf.do( "mkfs.ubifs -r %s -o %s.ubifs -m %s -e %s -c %s %s" % (
                os.path.join(target,"filesystems",label),
                os.path.join(target,label),
                ubivg.text("miniosize"),
                ubivg.text("logicaleraseblocksize"),
                ubivg.text("maxlogicaleraseblockcount"),
                fslabel[label].mkfsopt ) )
            # only append the ubifs file if creation didn't fail
            img_files.append ("%s.ubifs" % label)
        except CommandError as e:
            # continue creating further ubifs filesystems
            pass

    return img_files

def build_image_mtd( outf, mtd, target ):

    img_files = []

    if not mtd.has("ubivg"):
        return img_files

    ubivg = mtd.node("ubivg")

    cfgfilename = "%s_%s.cfg" % (mtd.text("name"), mtd.node("ubivg").text("label"))
    fp = open( os.path.join(target, cfgfilename ), "w" )

    for vol in mtd.node("ubivg"):
        if vol.has("label"):
            fp.write( "[%s]\n" % vol.text("label") )
            fp.write( "mode=ubi\n" )
            if not vol.has("empty"):
                if vol.has("binary"):
                    tmp = ""
                    # copy from target if path starts with /
                    if vol.text("binary")[0] == '/':
                        tmp = "target" + vol.text("binary")
                        img_files.append (tmp)
                        # img_files needs path relative to project dir
                        # ubinize cfg file needs absolute path
                        tmp = target + "/" + tmp
                    # copy from project directory
                    else:
                        tmp = target + "/" + vol.text("binary")
                    fp.write( "image=%s\n" % tmp )
                else:
                    fp.write( "image=%s.ubifs\n" % os.path.join(target,
                        vol.text("label")) )
            else:
                empt = open("/tmp/empty", "w" )
                empt.write("EMPTY")
                empt.close()
                fp.write( "image=/tmp/empty\n" )

            fp.write( "vol_type=%s\n" % vol.text("type") )
            fp.write( "vol_id=%s\n" % vol.text("id") )
            fp.write( "vol_name=%s\n" % vol.text("label") )

            if vol.text("size") != "remain":
                fp.write( "vol_size=%d\n" % size_to_int( vol.text("size") ) )

    fp.close()

    if ubivg.has("subpagesize"):
        subp = "-s " + ubivg.text("subpagesize")
    else:
        subp = ""

    try:
        outf.do( "ubinize %s -o %s -p %s -m %s %s/%s_%s.cfg" % (
            subp,
            os.path.join(target, mtd.text("name")),
            ubivg.text("physicaleraseblocksize"),
            ubivg.text("miniosize"),
            target,
            mtd.text("name"),
            ubivg.text("label") ) )
        # only add file to list if ubinize command was successful
        img_files.append (mtd.text("name"))

    except CommandError as e:
        # continue with generating further images
        pass

    return img_files

def size_to_int( size ):
    if size[-1] in digits:
        return int(size)

    if size.endswith( "M" ):
        unit = 1000*1000
        s = size[:-1]
    elif size.endswith( "MiB" ):
        unit = 1024*1024
        s = size[:-3]
    elif size.endswith( "MB" ):
        unit = 1000*1000
        s = size[:-2]
    if size.endswith( "G" ):
        unit = 1000*1000*1000
        s = size[:-1]
    elif size.endswith( "GiB" ):
        unit = 1024*1024*1024
        s = size[:-3]
    elif size.endswith( "GB" ):
        unit = 1000*1000*1000
        s = size[:-2]
    if size.endswith( "k" ):
        unit = 1000
        s = size[:-1]
    elif size.endswith( "kiB" ):
        unit = 1024
        s = size[:-3]
    elif size.endswith( "kB" ):
        unit = 1000
        s = size[:-2]

    return int(s) * unit


class grubinstaller( object ):
    def __init__( self, outf ):
        self.outf = outf
        self.root = None
        self.boot = None

    def set_boot_entry( self, entry ):
        print "setting boot entry"
        self.boot = entry

    def set_root_entry( self, entry ):
        self.root = entry

    def install( self, target ):
        if not self.root:
            return

        imagemnt = os.path.join(target, "imagemnt" )
        try:
            self.outf.do( 'cp -a /dev/loop0 /dev/poop0' )
            self.outf.do( 'cp -a /dev/loop1 /dev/poop1' )
            self.outf.do( 'cp -a /dev/loop2 /dev/poop2' )

            self.outf.do( 'losetup /dev/poop0 "%s"' % self.root.filename )
            self.root.losetup( self.outf, "poop1" )
            self.outf.do( 'mount /dev/poop1 %s' % imagemnt )

            if self.boot:
                self.boot.losetup( self.outf, "poop2" )
                self.outf.do( 'mount /dev/poop2 %s' % (os.path.join( imagemnt, "boot" ) ) )

            devmap = open( os.path.join( imagemnt, "boot/grub/device.map" ), "w" )
            devmap.write( "(hd0) /dev/poop0\n" )
            devmap.write( "(hd0,%s) /dev/poop1\n" % self.root.number )
            if self.boot:
                devmap.write( "(hd0,%s) /dev/poop2\n" % self.boot.number )

            devmap.close()


            self.outf.do( "mount --bind /dev %s" % os.path.join( imagemnt, "dev" ) )
            self.outf.do( "mount --bind /proc %s" % os.path.join( imagemnt, "proc" ) )
            self.outf.do( "mount --bind /sys %s" % os.path.join( imagemnt, "sys" ) )

            self.outf.do( "chroot %s  update-grub2"  % imagemnt )

            self.outf.do( "grub-install --no-floppy --grub-mkdevicemap=%s/boot/grub/device.map --root-directory=%s /dev/loop0" % (imagemnt,imagemnt))

        finally:
            self.outf.do( "umount %s" % os.path.join( imagemnt, "dev" ), allow_fail=True )
            self.outf.do( "umount %s" % os.path.join( imagemnt, "proc" ), allow_fail=True )
            self.outf.do( "umount %s" % os.path.join( imagemnt, "sys" ), allow_fail=True )

            self.outf.do( "losetup -d /dev/poop0", allow_fail=True )

            if self.boot:
                self.outf.do( 'umount /dev/poop2', allow_fail=True )
                self.outf.do( 'losetup -d /dev/poop2', allow_fail=True )

            self.outf.do( 'umount /dev/poop1', allow_fail=True )
            self.outf.do( 'losetup -d /dev/poop1', allow_fail=True )

class simple_fstype(object):
    def __init__(self, typ):
        self.type = typ

def do_image_hd( outf, hd, fslabel, target, grub_version ):

    # Init to 0 because we increment before using it
    partition_number = 0

    sector_size = 512
    s=size_to_int(hd.text("size"))
    size_in_sectors = s / sector_size

    imagename = os.path.join(target,hd.text("name"))
    outf.do( 'rm -f "%s"' % imagename, allow_fail=True )
    f = open( imagename, "wb" )
    f.truncate( size_in_sectors * sector_size )
    f.close()

    imag = parted.Device( imagename )
    if hd.tag == "gpthd":
        disk = parted.freshDisk(imag, "gpt" )
    else:
        disk = parted.freshDisk(imag, "msdos" )

    grub = grubinstaller( outf )

    current_sector = 2048
    for part in hd:

        if part.tag != "partition":
            continue

        if part.text("size") == "remain" and hd.tag == "gpthd":
            sz = size_in_sectors - 35 - current_sector
        elif part.text("size") == "remain":
            sz = size_in_sectors - current_sector
        else:
            sz = size_to_int(part.text("size"))/sector_size

        g = parted.Geometry (device=imag,start=current_sector,length=sz)
        if fslabel.has_key(part.text("label")) and fslabel[part.text("label")].fstype == "vfat": 
            fs = simple_fstype("fat32")
            ppart = parted.Partition(disk, parted.PARTITION_NORMAL, fs, geometry=g)
            ppart.setFlag(_ped.PARTITION_LBA)
        else:
            ppart = parted.Partition(disk, parted.PARTITION_NORMAL, geometry=g)

        cons = parted.Constraint(exactGeom=g)
        disk.addPartition(ppart, cons)

        if part.has("bootable"):
            ppart.setFlag(_ped.PARTITION_BOOT)

        if part.has("biosgrub"):
            ppart.setFlag(_ped.PARTITION_BIOS_GRUB)

        partition_number += 1

        if not fslabel.has_key(part.text("label")):
            current_sector += sz
            continue

        entry = fslabel[part.text("label")]
        entry.offset = current_sector*sector_size
        entry.size   = sz * sector_size
        entry.filename = imagename
        if hd.tag == "gpthd":
            entry.number = "gpt%d" % partition_number
        else:
            entry.number = "msdos%d" % partition_number


        if entry.mountpoint == "/":
            grub.set_root_entry( entry )
        elif entry.mountpoint == "/boot":
            grub.set_boot_entry( entry )

        entry.losetup( outf, "loop0" )
        outf.do( 'mkfs.%s %s %s /dev/loop0' % ( entry.fstype, entry.mkfsopt, entry.get_label_opt() ) )

        outf.do( 'mount /dev/loop0 %s' % os.path.join(target, "imagemnt" ) )
        outf.do( 'cp -a "%s"/* "%s"' % ( os.path.join( target, "filesystems", entry.label ), os.path.join(target, "imagemnt") ), allow_fail=True )
        outf.do( 'umount /dev/loop0' )
        outf.do( 'losetup -d /dev/loop0' )

        current_sector += sz

    disk.commit()

    if hd.has( "grub-install" ) and grub_version:
        grub.install( target )

    return hd.text("name")

def do_hdimg(outf, xml, target, rfs, grub_version):
    # list of created files
    img_files = []

    # Check whether we have any images first
    if not xml.tgt.has("images"):
        return img_files

    # Build a dictonary of mount points
    fslabel = {}
    for fs in xml.tgt.node("fstab"):
        if fs.tag != "bylabel":
            continue

        fslabel[fs.text("label")] = fstabentry(xml, fs)

    # Build a sorted list of mountpoints
    fslist = fslabel.values()
    fslist.sort( key = lambda x: x.mountdepth() )

    # now move all mountpoints into own directories
    # begin from deepest mountpoints

    fspath = os.path.join(target, "filesystems")
    outf.do( 'mkdir -p %s' % fspath )

    imagemnt = os.path.join(target, "imagemnt")
    outf.do( 'mkdir -p %s' % imagemnt )

    for l in reversed(fslist):
        outf.do( 'mkdir -p "%s"' % os.path.join( fspath, l.label ) )
        outf.do( 'mkdir -p "%s"' % rfs.fname('') + l.mountpoint )
        if len(rfs.listdir( l.mountpoint )) > 0:
            outf.do( 'mv "%s"/* "%s"' % ( rfs.fname(l.mountpoint), os.path.join(
                fspath, l.label ) ), allow_fail=True )

    try:
        # Now iterate over all images and create filesystems and partitions
        for i in xml.tgt.node("images"):
            if i.tag == "msdoshd":
                img = do_image_hd( outf, i, fslabel, target, grub_version )
                img_files.append (img)

            if i.tag == "gpthd":
                img = do_image_hd( outf, i, fslabel, target, grub_version )
                img_files.append (img)

            if i.tag == "mtd":
                imgs = mkfs_mtd( outf, i, fslabel, rfs, target )
                img_files.extend (imgs)
    finally:
        # Put back the filesystems into /target
        # most shallow fs first...
        for i in fslist:
            if len(os.listdir(os.path.join( fspath, i.label ))) > 0:
                outf.do( 'mv "%s"/* "%s"' % ( os.path.join( fspath, i.label ),
                    rfs.fname(i.mountpoint) ), allow_fail=True )

    # Files are now moved back. ubinize needs files in place, so we run it now.
    for i in xml.tgt.node("images"):
        if i.tag == "mtd":
            imgs = build_image_mtd( outf, i, target )
            img_files.extend (imgs)

    return img_files
