#!/usr/bin/env python

import os
import sys
import shutil

from treeutils import etree
from optparse import OptionParser
from subprocess import Popen, PIPE, STDOUT

import parted
import _ped

class commanderror(Exception):
    def __init__(self, cmd, returncode):
	self.returncode = returncode
	self.cmd = cmd

    def __repr__(self):
	return "Error: %d returned from Command %s" % (self.returncode, self.cmd)

class asccidoclog(object):
    def __init__(self):
	self.fp = sys.stdout

    def printo(self, text=""):
	self.fp.write(text+"\n")

    def print_raw(self, text):
	self.fp.write(text)

    def h1(self, text):
	self.printo()
	self.printo(text)
	self.printo("="*len(text))
	self.printo()

    def h2(self, text):
	self.printo()
	self.printo(text)
	self.printo("-"*len(text))
	self.printo()

    def table(self):
	self.printo( "|=====================================" )

    def verbatim_start(self):
	self.printo( "------------------------------------------------------------------------------" )

    def verbatim_end(self):
	self.printo( "------------------------------------------------------------------------------" )
	self.printo()

    def do_command(self, cmd):
	self.printo( "running cmd +%s+" % cmd )
	self.verbatim_start()
	p = Popen(cmd, shell=True, stdout=PIPE, stderr=STDOUT )
	output, stderr = p.communicate()
	self.print_raw( output )
	self.verbatim_end()

	if p.returncode != 0:
	    self.printo( "Command failed with errorcode %d" % p.returncode )
	    raise commanderror(cmd, p.returncode)

class fstabentry(object):
    def __init__(self, entry):
	self.label = entry.text("label")
	self.mountpoint = entry.text("mountpoint")
	if entry.has("fs"):
	    self.fstype = entry.text("fs/type")
            self.mkfsopt = entry.text("fs/mkfs", default="")

    def mountdepth(self):
	h = self.mountpoint
	depth = 0

	while True:
	    h, t = os.path.split(h) 
	    if t=='':
		return depth
	    depth += 0


    def get_label_opt(self):
        if self.fstype == "ext4":
            return "-L " + self.label
        if self.fstype == "ext2":
            return "-L " + self.label
        if self.fstype == "ext3":
            return "-L " + self.label
        if self.fstype == "vfat":
            return "-n " + self.label
        if self.fstype == "xfs":
            return "-L " + self.label
        if self.fstype == "btrfs":
            return "-L " + self.label

        return ""

def mkfs_mtd( outf, mtd, fslabel ):

    if not mtd.has("ubivg"):
        return

    ubivg = mtd.node("ubivg")
    for v in ubivg:

        label = v.text("label")

        if not fslabel.has_key(label):
            continue

        outf.do_command( "mkfs.ubifs -r /opt/elbe/filesystems/%s -o /opt/elbe/%s.ubifs -m %s -e %s -c %s %s" % (
            label, label,
            ubivg.text("miniosize"),
            ubivg.text("logicaleraseblocksize"),
            ubivg.text("maxlogicaleraseblockcount"),
            fslabel[label].mkfsopt ) )

def build_image_mtd( outf, mtd, fslabel ):

    if not mtd.has("ubivg"):
        return

    ubivg = mtd.node("ubivg")

    if ubivg.has("subpagesize"):
        subp = "-s " + ubivg.text("subpagesize")
    else:
        subp = ""

    outf.do_command( "ubinize %s -o %s -p %s -m %s /opt/elbe/ubi.cfg" % (
        subp,
        mtd.text("name"),
        ubivg.text("physicaleraseblocksize"),
        ubivg.text("miniosize") ) )

    outf.do_command( "echo /opt/elbe/%s >> /opt/elbe/files-to-extract" % mtd.text("name") )




def do_image_hd( outf, hd, fslabel ):

	if not hd.has("partitions"):
	    return

	s=int(hd.text("size"))
	c=(s*1000*1024)/(16*63*512)

	outf.do_command( 'dd if=/dev/zero of="%s" count=%d bs=516096' % (hd.text("name"), c) )
	imag = parted.Device( hd.text("name") )
	disk = parted.freshDisk(imag, "msdos" )

        outf.do_command( 'echo /opt/elbe/' + hd.text("name") + ' >> /opt/elbe/files-to-extract' )

	current_sector = 63
	for part in hd.node("partitions"):
	    if part.text("size") == "remain":
		sz = (c*16*63) - current_sector;
	    else:
		sz = int(part.text("size"))

	    g = parted.Geometry (device=imag,start=current_sector,length=sz)
	    ppart = parted.Partition(disk, parted.PARTITION_NORMAL, geometry=g)
	    cons = parted.Constraint(exactGeom=g)
	    disk.addPartition(ppart, cons)

	    if part.has("bootable"):
		ppart.setFlag(_ped.PARTITION_BOOT)

            if not fslabel.has_key(part.text("label")):
                current_sector += sz
                continue

	    entry = fslabel[part.text("label")]
	    entry.offset = current_sector*512
	    entry.size   = sz * 512
	    entry.filename = hd.text("name")

	    outf.do_command( 'losetup -o%d --sizelimit %d /dev/loop0 "%s"' % (entry.offset, entry.size,entry.filename) )
	    outf.do_command( 'mkfs.%s %s %s /dev/loop0' % ( entry.fstype, entry.mkfsopt, entry.get_label_opt() ) )

            outf.do_command( 'mount /dev/loop0 %s' % opt.dir )
            outf.do_command( 'cp -a "%s"/* "%s"' % ( os.path.join( '/opt/elbe/filesystems', entry.label ), opt.dir ) )
            outf.do_command( 'umount /dev/loop0' )
	    outf.do_command( 'losetup -d /dev/loop0' )

	    current_sector += sz

	disk.commit()


def run_command( argv ):

    oparser = OptionParser( usage="usage: %prog hdimg <xmlfile>")
    oparser.add_option( "--directory", dest="dir",
                        help="mount the loop file here",
                        metavar="FILE" )
    oparser.add_option( "--umount", action="store_true", dest="umount",
                        default=False,
			help="Just umount the specified partitions" )

    (opt,args) = oparser.parse_args(argv)

    if len(args) != 1:
	print "Wrong number of arguments"
	oparser.print_help()
	sys.exit(20)

    if not opt.dir:
	print "No mount directory specified!"
	oparser.print_help()
	sys.exit(20)

    try:
	xml = etree( args[0] )
    except:
	print "Error reading xml file!"
	sys.exit(20)

    tgt = xml.node("target")

    if not tgt.has("images"):
	print "no images defined"
	sys.exit(20)

    if not tgt.has("fstab"):
	print "no fstab defined"
	sys.exit(20)

    outf = asccidoclog()
    outf.h2( "Formatting Disks" )

    # Build a dictonary of mount points
    fslabel = {}
    for fs in tgt.node("fstab"):
	if fs.tag != "bylabel":
	    continue

	fslabel[fs.text("label")] = fstabentry(fs)

    # Build a sorted list of mountpoints
    fslist = fslabel.values()
    fslist.sort( key = lambda x: x.mountdepth() )

    # now move all mountpoints into own directories
    # begin from deepest mountpoints

    outf.do_command( 'mkdir -p /opt/elbe/filesystems' )

    for l in reversed(fslist):
        outf.do_command( 'mkdir -p "%s"' % os.path.join( '/opt/elbe/filesystems', l.label ) )
        outf.do_command( 'mv "%s"/* "%s"' % ( '/target' + l.mountpoint, os.path.join( '/opt/elbe/filesystems', l.label ) ) )

    try:
	# Now iterate over all images and create filesystems and partitions
	for i in tgt.node("images"):
	    if i.tag == "hd":
		do_image_hd( outf, i, fslabel )

	    if i.tag == "mtd":
		mkfs_mtd( outf, i, fslabel )
    finally:
	# Put back the filesystems into /target
	# most shallow fs first...
	for i in fslist:
	    outf.do_command( 'mv "%s"/* "%s"' % ( os.path.join( '/opt/elbe/filesystems', i.label ), '/target' + i.mountpoint ) )

    # Files are now moved back. ubinize needs files in place, so we run it now.
    for i in tgt.node("images"):
	if i.tag == "mtd":
	    build_image_mtd( outf, i, fslabel )


if __name__ == "__main__":
    run_command( sys.argv[1:] )
    
