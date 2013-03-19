## ELBE - Debian Based Embedded Rootfilesystem Builder
## Copyright (C) 2013  Linutronix GmbH
##
## This file is part of ELBE.
##
## ELBE is free software: you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation, either version 3 of the License, or
## (at your option) any later version.
##
## ELBE is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.
##
## You should have received a copy of the GNU General Public License
## along with ELBE.  If not, see <http://www.gnu.org/licenses/>.
##
IMGSIZE=${prj.text("buildimage/size")}
MEMSIZE=${prj.text("buildimage/mem")}
SMP?=1

<% 
import string

if prj.text("suite")=="squeeze" and prj.text("buildimage/interpreter") == "qemu-system-ppc":
  loop_offset = 32768 
elif prj.text("suite")=="squeeze":
  loop_offset = 2048*512
else:
  loop_offset = 32256

if prj.text("buildimage/interpreter") == "kvm":
  hd_type = "virtio"
  cdrom_type = "scsi"
  hd_name = "vda1"
elif prj.text("buildimage/interpreter") == "qemu-system-ppc":
  hd_type = "ide"
  cdrom_type = "ide"
  hd_name = "hdc2"
else:
  hd_type = "scsi"
  cdrom_type = "scsi"
  hd_name = "sda1"

all_targets = ["stamp-feed-initial-image", "install.iso", "elbe-report.txt", "source.xml"]
if xml.has("target/package/tar"):
  all_targets.append( tgt.text("package/tar/name") )
if xml.has("target/package/cpio"):
  all_targets.append( tgt.text("package/cpio/name") )
if opt.debug:
  all_targets.append( "stamp-install-log" )
if xml.has("target/pkg-list/git-src") or xml.has("target/pkg-list/svn-src"):
  all_targets.append( "get-deb-pkgs" )
if xml.has("fullpkgs"):
  all_targets.append( "validation.txt" )
if opt.buildsources:
  all_targets.append( "source.iso" )
all_targets = string.join( all_targets )

target_num = 1
%>

all: ${all_targets}

initrd-preseeded.gz: *.cfg post-inst.sh create-target-rfs.sh pkg-list finetuning.sh changeroot-into-buildenv.sh cp-scipts-into-buildenv.sh
	rm -rf tmp-tree
	mkdir tmp-tree
	cp *.cfg tmp-tree/
	-cp preferences tmp-tree/
	mkdir -p tmp-tree/usr/lib/post-base-installer.d
	cp 02pinning tmp-tree/usr/lib/post-base-installer.d
	cp post-inst.sh tmp-tree/
	cp create-target-rfs.sh tmp-tree/
	cp cp-scipts-into-buildenv.sh tmp-tree/
	cp changeroot-into-buildenv.sh tmp-tree/
	cp pkg-list tmp-tree/
	cp Release.bin Release.src tmp-tree/
	cp part-target.sh tmp-tree/
	cp print_licence.sh tmp-tree/
	cp finetuning.sh tmp-tree/
	cp purge.sh tmp-tree/
	cp source.xml tmp-tree/
	cp dump.py tmp-tree/
	cp treeutils.py tmp-tree/
	cp ubi.cfg tmp-tree/
	cp fstab tmp-tree/
	cp pkg-selections tmp-tree/
	cp mkcdrom.sh tmp-tree/
% if xml.has("archive"):
	cp archive.tar.bz2 tmp-tree/
% endif
	gzip -cd initrd.gz >initrd-preseeded
	cd tmp-tree && find . | cpio -H newc -o --append -F ../initrd-preseeded
	gzip -9f initrd-preseeded
	rm -rf tmp-tree

stamp-create-buildenv-img buildenv.img: initrd-preseeded.gz
	qemu-img create -f raw buildenv.img $(IMGSIZE)
	touch stamp-create-buildenv-img

stamp-install-initial-image: stamp-create-buildenv-img
	${prj.text("buildimage/interpreter")}  \
		-M ${prj.text("buildimage/machine")} \
% if opt.oldkvm:
		-drive file=buildenv.img,if=${hd_type},index=0,boot=on \
% else:
		-drive file=buildenv.img,if=${hd_type},bus=1,unit=0 \
% endif
% if prj.has("mirror/cdrom"):
  -drive file=${prj.text("mirror/cdrom")},if=${cdrom_type},media=cdrom,bus=1,unit=1 \
% endif
		-kernel vmlinuz \
		-initrd initrd-preseeded.gz \
		-append 'root=/dev/${hd_name} debconf_priority=critical console=${prj.text("buildimage/console")} DEBIAN_FRONTEND=newt' \
		-no-reboot \
% if not opt.debug:
		-nographic \
% endif
		-net nic,vlan=1,model=${prj.text("buildimage/NIC/model")},macaddr="${prj.text('buildimage/NIC/MAC')}" \
		-net user,vlan=1 \
		-m $(MEMSIZE) \
		-usb && reset
	touch stamp-install-initial-image

stamp-feed-initial-image: stamp-install-initial-image
	touch stamp-feed-initial-image

run: stamp-feed-initial-image
	${prj.text("buildimage/interpreter")}  \
		-M ${prj.text("buildimage/machine")} \
% if opt.oldkvm:
		-drive file=buildenv.img,if=${hd_type},index=0,boot=on \
% else:
		-drive file=buildenv.img,if=${hd_type},bus=1,unit=0 \
% endif
		-no-reboot \
		-net nic,vlan=1,model=${prj.text("buildimage/NIC/model")},macaddr="${prj.text('buildimage/NIC/MAC')}" \
		-net user,vlan=1 \
		-m $(MEMSIZE) \
		-usb \
% if prj.has("mirror/cdrom"):
		-drive file=${prj.text("mirror/cdrom")},if=${hd_type},media=cdrom,bus=1,unit=1 \
% endif
% if xml.text("project/buildimage/arch") == "armel" or xml.text("project/buildimage/arch") == "powerpc":
% if prj.text("suite")=="squeeze":
		-kernel vmlinu* \
		-initrd initrd.img-* \
% else:
		-kernel vmlin* \
		-initrd initrd* \
% endif
		-append 'root=/dev/${hd_name}' \
% endif
		-smp $(SMP) \
% if prj.has("buildimage/portforwarding"):
% for f in prj.node("buildimage/portforwarding"):
		-redir ${f.text("proto")}:${f.text("host")}::${f.text("buildenv")} \
% endfor
% endif
	&& reset
run-con: stamp-feed-initial-image
	${prj.text("buildimage/interpreter")}  \
		-M ${prj.text("buildimage/machine")} \
% if opt.oldkvm:
		-drive file=buildenv.img,if=${hd_type},index=0,boot=on \
% else:
		-drive file=buildenv.img,if=${hd_type},bus=1,unit=0 \
% endif
		-no-reboot \
		-net nic,vlan=1,model=${prj.text("buildimage/NIC/model")},macaddr="${prj.text('buildimage/NIC/MAC')}" \
		-net user,vlan=1 \
		-m $(MEMSIZE) \
		-usb \
		-nographic \
% if prj.has("mirror/cdrom"):
		-drive file=${prj.text("mirror/cdrom")},if=${hd_type},media=cdrom,bus=1,unit=1 \
% endif
% if xml.text("project/buildimage/arch") == "armel" or xml.text("project/buildimage/arch") == "powerpc":
% if prj.text("suite")=="squeeze":
		-kernel vmlinu* \
		-initrd initrd.img-* \
% else:
		-kernel vmlin* \
		-initrd initrd* \
% endif
		-append 'root=/dev/${hd_name}' \
% endif
		-smp $(SMP) \
% if prj.has("buildimage/portforwarding"):
% for f in prj.node("buildimage/portforwarding"):
		-redir ${f.text("proto")}:${f.text("host")}::${f.text("buildenv")} \
% endfor
% endif
	&& reset

files-to-extract: stamp-feed-initial-image
	e2cp buildenv.img?offset=${loop_offset}:/opt/elbe/files-to-extract .
	for f in `cat files-to-extract`; do e2cp  buildenv.img?offset=${loop_offset}:$$f . ; done

% if xml.has("target/package/tar"):
${xml.text("target/package/tar/name")}: files-to-extract 
	gzip target.tar
	mv target.tar.gz ${xml.text("target/package/tar/name")}
% endif

% if xml.has("target/pkg-list/git-src") or xml.has("target/pkg-list/svn-src"):
get-deb-pkgs: files-to-extract
	mkdir -p deb-archive
	tar xf builds.tar -C deb-archive
% endif


% if xml.has("fullpkgs"):
validation.txt: files-to-extract
	cat validation.txt
% endif


stamp-pack-build-image: stamp-feed-initial-image
	bzip2 -9 buildenv.img
	touch stamp-pack-build-image

clean:
	rm -f stamp* buildenv.img initrd-preseeded.gz

distclean: clean
	rm -rf tmp-mount tmp-target
	rm -f *cfg initrd.gz pkg-list *.sh vmlinuz Makefile Release.bin  Release.src 02pinning preferences ubi.cfg fstab
