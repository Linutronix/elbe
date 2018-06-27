## ELBE - Debian Based Embedded Rootfilesystem Builder
## Copyright (c) 2014-2017 Torben Hohn <torben.hohn@linutronix.de>
## Copyright (c) 2014-2017 Manuel Traut <manut@linutronix.de>
## Copyright (c) 2017 Lukasz Walewski <lwalewski@s-can.at>
##
## SPDX-License-Identifier: GPL-3.0-or-later
##
MEMSIZE?=1024
SMP?=`nproc`
INTERPRETER?=${prj.text('interpreter', default=defs, key='interpreter')}

# this is a workaround for
# http://lists.linutronix.de/pipermail/elbe-devel/2017-July/000541.html
VIRT=$(shell test -x /usr/bin/systemd-detect-virt && /usr/bin/systemd-detect-virt)
DIST=$(shell lsb_release -cs)
ifeq ($(filter-out vmware stretch, $(VIRT) $(DIST)),)
MACHINE?=pc-i440fx-2.6
else
MACHINE?=pc
endif

NICMODEL?=virtio
CONSOLE?=ttyS0,115200n1
LOOP_OFFSET?=1048576
HD_TYPE?=virtio
HD_NAME?=vda1
CDROM_TYPE?=ide

<%
import string
img = prj.text('img', default=defs, key='img')
imgsize = prj.text('size', default=defs, key='size')
nicmac = prj.text('buildimage/NIC/MAC', default=defs, key='nicmac')
target_num = 1

interpreter_v_major = int(prj.text('interpreterversion',
                                   default=defs,
                                   key='interpreterversion').split('.')[0])

interpreter_v_minor = int(prj.text('interpreterversion',
                                   default=defs,
                                   key='interpreterversion').split('.')[1])
fwd = ""
if prj.has("portforwarding"):
	for f in prj.node("portforwarding"):
		fwd += ",hostfwd=%s::%s-:%s" % (f.text("proto"),
																		f.text("host"),
																		f.text("buildenv"))
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
	mkdir -p tmp-tree/usr/share/keyrings
	-cp .elbe-in/*.gpg tmp-tree/usr/share/keyrings
% if opt.devel:
	cp .elbe-in/elbe-devel.tar.bz2 tmp-tree/
% endif
% if opt.cdrom:
	mkdir -p tmp-tree/usr/lib/base-installer.d
	echo 'mkdir -p /target/etc/apt/trusted.gpg.d/; cp /usr/share/keyrings/elbe-keyring.gpg /target/etc/apt/trusted.gpg.d/' > tmp-tree/usr/lib/base-installer.d/10copyelbekeyring
	chmod 755 tmp-tree/usr/lib/base-installer.d/*
% endif
	mkdir -p .elbe-gen
	gzip -cd .elbe-in/initrd.gz >.elbe-gen/initrd-preseeded
	cd tmp-tree && find . | cpio -H newc -o --append -F ../.elbe-gen/initrd-preseeded
	gzip -9f .elbe-gen/initrd-preseeded
	rm -rf tmp-tree

.stamps/stamp-create-buildenv-img buildenv.img: .elbe-gen/initrd-preseeded.gz
	qemu-img create -f ${img} buildenv.img ${imgsize}
	mkdir -p .stamps
	touch .stamps/stamp-create-buildenv-img

.stamps/stamp-install-initial-image: .stamps/stamp-create-buildenv-img
	@ echo $(INTERPRETER)
	@ $(INTERPRETER) -M $(MACHINE) \
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
		-smp $(SMP) \
		-usb \
		|| ( echo; \
		     echo "------------------------------------------------------------------"; \
		     echo "kvm failed to start"; \
		     echo "This is most likely the case, because /dev/kvm is not available."; \
		     echo "To use KVM inside a VMWARE or other VM instance,"; \
		     echo "nested KVM needs to be supported"; \
		     echo "------------------------------------------------------------------"; \
		     echo; \
		     false \
		)

	mkdir -p .stamps
	touch .stamps/stamp-install-initial-image

run:
	$(INTERPRETER) -M $(MACHINE) \
		-device virtio-rng-pci \
		-device virtio-net-pci,netdev=user.0 \
		-drive file=buildenv.img,if=$(HD_TYPE),bus=1,unit=0 \
		-no-reboot \
% if ((interpreter_v_major == 2) and (interpreter_v_minor >= 8)) or (interpreter_v_major > 2):
		-netdev user,ipv4,id=user.0${fwd} \
% else:
		-netdev user,id=user.0${fwd} \
% endif
% if opt.nesting:
		-cpu host \
% endif
		-m $(MEMSIZE) \
		-usb \
		-smp $(SMP)

run-con:
	$(INTERPRETER) -M $(MACHINE) \
		-device virtio-rng-pci \
		-device virtio-net-pci,netdev=user.0 \
		-drive file=buildenv.img,if=$(HD_TYPE),bus=1,unit=0 \
		-no-reboot \
% if ((interpreter_v_major == 2) and (interpreter_v_minor >= 8)) or (interpreter_v_major > 2):
		-netdev user,ipv4,id=user.0${fwd} \
% else:
		-netdev user,id=user.0${fwd} \
% endif
% if opt.nesting:
		-cpu host \
% endif
		-m $(MEMSIZE) \
		-usb \
		-nographic \
		-smp $(SMP)

clean:
	rm -fr .stamps/stamp* buildenv.img .elbe-vm .elbe-gen

distclean: clean
	echo clean
