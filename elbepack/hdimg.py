#!/usr/bin/env python

import os
import sys
import shutil

from treeutils import etree
from optparse import OptionParser

import parted

class fstabentry(object):
    def __init__(self, entry):
	self.label = entry.text("label")
	self.mountpoint = entry.text("mountpoint")
	if entry.has("fs"):
	    self.fstype = entry.text("fs/type")

    def mountdepth(self):
	h = self.mountpoint
	depth = 0

	while True:
	    h, t = os.path.split(h) 
	    if t=='':
		return depth
	    depth += 0
	
	    

def run_command( argv ):

    oparser = OptionParser( usage="usage: %prog hdimg <xmlfile>")
    oparser.add_option( "--directory", dest="dir",
                        help="mount the loop file here",
                        metavar="FILE" )
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

    fslabel = {}
    for fs in tgt.node("fstab"):
	if fs.tag != "bylabel":
	    continue

	fslabel[fs.text("label")] = fstabentry(fs)


    for hd in tgt.node("images"):
	if not hd.tag == "hd":
	    continue

	if not hd.has("partitions"):
	    continue

	print hd.tag
	s=int(hd.text("size"))
	c=(s*1000*1024)/(16*63*512)

	os.system( 'dd if=/dev/zero of="%s" count=%d bs=516096' % (hd.text("name"), c) )
	imag = parted.Device( hd.text("name") )
	disk = parted.freshDisk(imag, "msdos" )

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

	    entry = fslabel[part.text("label")]
	    entry.offset = current_sector*512
	    entry.size   = sz * 512
	    entry.filename = hd.text("name")

	    print 'losetup -o%d --sizelimit %d /dev/loop0 "%s"' % (entry.offset, entry.size,entry.filename)
	    print 'mkfs.%s /dev/loop0' % ( entry.fstype )
	    print 'losetup -d /dev/loop0'

	    current_sector += sz

	disk.commit()

    fslist = fslabel.values()
    fslist.sort( key = lambda x: x.mountdepth() )

    for i in fslist:
	print 'mkdir -p "%s"' % ( opt.dir + i.mountpoint )
	print 'mount -o loop,offset=%d,sizelimit=%d "%s" "%s"' % (i.offset, i.size, i.filename, opt.dir + i.mountpoint)


if __name__ == "__main__":
    run_command( sys.argv[1:] )
    
