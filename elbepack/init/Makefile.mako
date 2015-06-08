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
IMGSIZE?=20G
MEMSIZE?=1024
SMP?=`nproc`
INTERPRETER?=kvm
MACHINE?=pc
NICMODEL?=virtio
CONSOLE?=ttyS0,115200n1
LOOP_OFFSET?=1048576
HD_TYPE?=virtio
HD_NAME?=vda1
CDROM_TYPE?=ide

<%
import string

nicmac = prj.text('buildimage/NIC/MAC', default=defs, key='nicmac')
target_num = 1
%>

all: .stamps/stamp-install-initial-image

.elbe-gen/initrd-preseeded.gz: .elbe-in/*
	rm -rf tmp-tree
	mkdir tmp-tree
	cp .elbe-in/*.cfg tmp-tree/
	-cp .elbe-in/apt.conf tmp-tree/
	mkdir -p tmp-tree/etc/apt
	-cp .elbe-in/apt.conf tmp-tree/etc/apt
	mkdir -p tmp-tree/usr/lib/post-base-installer.d
	cp .elbe-in/init-elbe.sh tmp-tree/
	cp .elbe-in/source.xml tmp-tree/
% if opt.devel:
	cp .elbe-in/elbe-devel.tar.bz2 tmp-tree/
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
	$(INTERPRETER) -M $(MACHINE) \
		-device virtio-rng-pci \
		-drive file=buildenv.img,if=$(HD_TYPE),bus=1,unit=0 \
% if prj.has("mirror/cdrom"):
		-drive file=${prj.text("mirror/cdrom")},if=$(CDROM_TYPE),media=cdrom,bus=1,unit=0 \
% endif
		-kernel .elbe-in/vmlinuz \
		-initrd .elbe-gen/initrd-preseeded.gz \
		-append 'root=/dev/$(HD_NAME) debconf_priority=critical console=$(CONSOLE) DEBIAN_FRONTEND=text' \
		-no-reboot \
		-nographic \
		-net nic,vlan=1,model=$(NICMODEL),macaddr="${nicmac}" \
		-net user,vlan=1 \
		-m $(MEMSIZE) \
		-usb
	mkdir -p .stamps
	touch .stamps/stamp-install-initial-image

run:
	$(INTERPRETER) -M $(MACHINE) \
		-device virtio-rng-pci \
		-drive file=buildenv.img,if=$(HD_TYPE),bus=1,unit=0 \
		-no-reboot \
		-net nic,vlan=1,model=$(NICMODEL),macaddr="${nicmac}" \
		-net user,vlan=1 \
% if prj.has("portforwarding"):
% for f in prj.node("portforwarding"):
		-redir ${f.text("proto")}:${f.text("host")}::${f.text("buildenv")} \
% endfor
% endif
		-m $(MEMSIZE) \
		-usb \
		-smp $(SMP)

run-con:
	$(INTERPRETER) -M $(MACHINE) \
		-device virtio-rng-pci \
		-drive file=buildenv.img,if=$(HD_TYPE),bus=1,unit=0 \
		-no-reboot \
		-net nic,vlan=1,model=$(NICMODEL),macaddr="${nicmac}" \
		-net user,vlan=1 \
% if prj.has("portforwarding"):
% for f in prj.node("portforwarding"):
		-redir ${f.text("proto")}:${f.text("host")}::${f.text("buildenv")} \
% endfor
% endif
		-m $(MEMSIZE) \
		-usb \
		-nographic \
		-smp $(SMP)

clean:
	rm -fr .stamps/stamp* buildenv.img .elbe-vm .elbe-gen

distclean: clean
	echo clean
