#!/usr/bin/env python

import os
import sys
import shutil

from treeutils import etree
from optparse import OptionParser

import parted

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

    fslabel = {}
    for fs in tgt.node("fstab"):
	if fs.tag != "bylabel":
	    continue

	fslabel[fs.text("label")] = fstabentry(fs)

    fslist = fslabel.values()
    fslist.sort( key = lambda x: x.mountdepth() )

    if opt.umount:
	fslist.reverse()
	for i in fslist:
	    outf.do_commandi( 'umount "%s"' % (opt.dir + i.mountpoint) )
	sys.exit(0)

    for hd in tgt.node("images"):
	if not hd.tag == "hd":
	    continue

	if not hd.has("partitions"):
	    continue

	print hd.tag
	s=int(hd.text("size"))
	c=(s*1000*1024)/(16*63*512)

	outf.do_command( 'dd if=/dev/zero of="%s" count=%d bs=516096' % (hd.text("name"), c) )
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

	    outf.do_command( 'losetup -o%d --sizelimit %d /dev/loop0 "%s"' % (entry.offset, entry.size,entry.filename) )
	    outf.do_command( 'mkfs.%s /dev/loop0' % ( entry.fstype ) )
	    outf.do_command( 'losetup -d /dev/loop0' )

	    current_sector += sz

	disk.commit()

    for i in fslist:
	outf.do_command( 'mkdir -p "%s"' % ( opt.dir + i.mountpoint ) )
	outf.do_command( 'mount -o loop,offset=%d,sizelimit=%d "%s" "%s"' % (i.offset, i.size, i.filename, opt.dir + i.mountpoint) )


if __name__ == "__main__":
    run_command( sys.argv[1:] )
    
