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

  all_targets = [".stamps/stamp-install-initial-image", ".elbe-gen/files-to-extract"]
if xml.has("target/package/tar"):
  all_targets.append( tgt.text("package/tar/name") )
if xml.has("target/package/cpio"):
  all_targets.append( tgt.text("package/cpio/name") )
if opt.debug:
  all_targets.append( ".stamps/stamp-install-log" )
if xml.has("target/pkg-list/git-src") or xml.has("target/pkg-list/svn-src"):
  all_targets.append( "get-deb-pkgs" )
if xml.has("fullpkgs"):
  all_targets.append( "validation.txt" )
all_targets = string.join( all_targets )

target_num = 1
%>

all: ${all_targets}

.elbe-gen/initrd-preseeded.gz: .elbe-in/*
	rm -rf tmp-tree
	mkdir tmp-tree
	cp .elbe-in/*.cfg tmp-tree/
	-cp .elbe-in/preferences tmp-tree/
	mkdir -p tmp-tree/usr/lib/post-base-installer.d
	cp .elbe-in/02pinning tmp-tree/usr/lib/post-base-installer.d
	cp .elbe-in/post-inst.sh tmp-tree/
	cp .elbe-in/create-target-rfs.sh tmp-tree/
	cp .elbe-in/cp-scipts-into-buildenv.sh tmp-tree/
	cp .elbe-in/changeroot-into-buildenv.sh tmp-tree/
	cp .elbe-in/pkg-list tmp-tree/
	cp .elbe-in/Release.bin .elbe-in/Release.src tmp-tree/
	cp .elbe-in/part-target.sh tmp-tree/
	cp .elbe-in/print_licence.sh tmp-tree/
	cp .elbe-in/finetuning.sh tmp-tree/
	cp .elbe-in/purge.sh tmp-tree/
	cp .elbe-in/source.xml tmp-tree/
	cp .elbe-in/dump.py tmp-tree/
	cp .elbe-in/treeutils.py tmp-tree/
	cp .elbe-in/ubi.cfg tmp-tree/
	cp .elbe-in/fstab tmp-tree/
	cp .elbe-in/pkg-selections tmp-tree/
	cp .elbe-in/mkcdrom.sh tmp-tree/
% if xml.has("archive"):
	cp .elbe-in/archive.tar.bz2 tmp-tree/
% endif
	mkdir -p .elbe-gen
	gzip -cd .elbe-in/initrd.gz >.elbe-gen/initrd-preseeded
	cd tmp-tree && find . | cpio -H newc -o --append -F ../.elbe-gen/initrd-preseeded
	gzip -9f .elbe-gen/initrd-preseeded
	rm -rf tmp-tree

.stamps/stamp-create-buildenv-img buildenv.img: .elbe-gen/initrd-preseeded.gz
	qemu-img create -f raw buildenv.img $(IMGSIZE)
	mkdir -p .stamps
	touch .stamps/stamp-create-buildenv-img

.stamps/stamp-install-initial-image: .stamps/stamp-create-buildenv-img
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
		-kernel .elbe-in/vmlinuz \
		-initrd .elbe-gen/initrd-preseeded.gz \
		-append 'root=/dev/${hd_name} debconf_priority=critical console=${prj.text("buildimage/console")} DEBIAN_FRONTEND=newt' \
		-no-reboot \
% if not opt.debug:
		-nographic \
% endif
		-net nic,vlan=1,model=${prj.text("buildimage/NIC/model")},macaddr="${prj.text('buildimage/NIC/MAC')}" \
		-net user,vlan=1 \
		-m $(MEMSIZE) \
		-usb && reset
	mkdir -p .stamps
	touch .stamps/stamp-install-initial-image

run: .elbe-gen/files-to-extract
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
% if prj.text("suite")=="squeeze":
		-kernel vmlinu* \
		-initrd initrd.img-* \
% else:
		-kernel vmlin* \
		-initrd initrd* \
% endif
		-append 'root=/dev/${hd_name}' \
		-smp $(SMP) \
% if prj.has("buildimage/portforwarding"):
% for f in prj.node("buildimage/portforwarding"):
		-redir ${f.text("proto")}:${f.text("host")}::${f.text("buildenv")} \
% endfor
% endif
	&& reset
run-con: .elbe-gen/files-to-extract
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
% if prj.text("suite")=="squeeze":
		-kernel vmlinu* \
		-initrd initrd.img-* \
% else:
		-kernel vmlin* \
		-initrd initrd* \
% endif
		-append 'root=/dev/${hd_name}' \
		-smp $(SMP) \
% if prj.has("buildimage/portforwarding"):
% for f in prj.node("buildimage/portforwarding"):
		-redir ${f.text("proto")}:${f.text("host")}::${f.text("buildenv")} \
% endfor
% endif
	&& reset

.elbe-gen/files-to-extract: .stamps/stamp-install-initial-image
	mkdir -p .elbe-gen
	e2cp buildenv.img?offset=${loop_offset}:/opt/elbe/files-to-extract .elbe-gen/
	for f in `cat .elbe-gen/files-to-extract`; do e2cp  buildenv.img?offset=${loop_offset}:$$f . ; done

% if xml.has("target/package/tar"):
${xml.text("target/package/tar/name")}: .elbe-gen/files-to-extract
	gzip target.tar
	mv target.tar.gz ${xml.text("target/package/tar/name")}
% endif

% if xml.has("target/pkg-list/git-src") or xml.has("target/pkg-list/svn-src"):
get-deb-pkgs: ./elbe-gen/files-to-extract
	mkdir -p deb-archive
	tar xf builds.tar -C deb-archive
% endif


% if xml.has("fullpkgs"):
validation.txt: .elbe-gen/files-to-extract
	cat validation.txt
% endif


.stamps/stamp-pack-build-image: .stamps/stamp-install-initial-image
	bzip2 -9 buildenv.img
	mkdir -p .stamps
	touch .stamps/stamp-pack-build-image

clean:
	rm -f .stamps/stamp* buildenv.img initrd-preseeded.gz

distclean: clean
	rm -rf tmp-mount tmp-target
	rm -f *cfg initrd.gz pkg-list *.sh vmlinuz Makefile Release.bin  Release.src 02pinning preferences ubi.cfg fstab
