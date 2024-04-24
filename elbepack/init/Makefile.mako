## ELBE - Debian Based Embedded Rootfilesystem Builder
## SPDX-License-Identifier: GPL-3.0-or-later
## SPDX-FileCopyrightText: 2014-2017 Linutronix GmbH
## SPDX-FileCopyrightText: 2017 Lukasz Walewski <lwalewski@s-can.at>

<%
import multiprocessing
from elbepack.filesystem import size_to_int

max_cpus = int(prj.text('max-cpus', default=defs, key='max-cpus'))
memory = size_to_int(prj.text('mem', default=defs, key='mem')) // 1024 // 1024
%>

MEMSIZE?=${memory}
SMP?=$$((`nproc` > ${max_cpus} ? ${max_cpus} : `nproc`))
INTERPRETER?=${prj.text('interpreter', default=defs, key='interpreter')}
% if defs["interpreter-args"] is not None:
INTERPRETER-ARGS= ${" ".join(defs["interpreter-args"])}
% endif
MACHINE?=pc

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

fwd = ""
if prj.has("portforwarding"):
    for f in prj.node("portforwarding"):
        fwd += ",hostfwd=%s::%s-:%s" % (f.text("proto"),
                                        f.text("host"),
                                        f.text("buildenv"))
%>


GEN=.elbe-gen
IN=.elbe-in

INITRD=$(GEN)/initrd-preseeded
VMLINUZ=$(IN)/vmlinuz

INITRD_FILES=$(shell find $(IN)/initrd-tree -type f)

BASE=initvm-base.img
INITVM=initvm.img

CLEAN=$(BASE) $(INITVM) $(GEN)

all: $(INITVM)

$(INITVM): $(BASE)
	qemu-img create -f ${img} -F ${img} -b $< $@

$(BASE): $(INITRD)
	qemu-img create -f ${img} $@ ${imgsize}
	@ echo $(INTERPRETER)
	@ $(INTERPRETER) -M $(MACHINE) \
		$(INTERPRETER-ARGS) \
		-device virtio-rng-pci \
		-drive file=$@,if=$(HD_TYPE),bus=1,unit=0 \
% if prj.has("mirror/cdrom"):
		-drive file=${prj.text("mirror/cdrom")},if=$(CDROM_TYPE),media=cdrom,bus=1,unit=0 \
% endif
		-kernel $(VMLINUZ) \
		-initrd $(INITRD)  \
		-append 'root=/dev/$(HD_NAME) debconf_priority=critical console=$(CONSOLE) DEBIAN_FRONTEND=text TERM=dumb' \
		-no-reboot \
		-display none \
		-monitor none \
		-serial stdio \
		-serial file:installer.log \
		-device virtio-net-pci,netdev=user.0,mac="${nicmac}" \
		-netdev user,id=user.0 \
		-m $(MEMSIZE) \
		-smp $(SMP) \
		-usb \
		-cpu host \
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

$(INITRD): $(INITRD_FILES)
	mkdir -p $(IN)/initrd-tree/usr/lib/base-installer.d $(IN)/initrd-tree/lib/debian-installer-startup.d
	echo 'mkdir -p /target/etc/apt/trusted.gpg.d/; cp /usr/share/keyrings/elbe-keyring.gpg /target/etc/apt/trusted.gpg.d/' > $(IN)/initrd-tree/usr/lib/base-installer.d/10copyelbekeyring
	echo "echo 'ttyS1::respawn:/usr/bin/tail -n +0 -f /var/log/syslog' >> /etc/inittab; kill -HUP 1" > $(IN)/initrd-tree/lib/debian-installer-startup.d/S10serial-log
	chmod 755 $(IN)/initrd-tree/usr/lib/base-installer.d/* $(IN)/initrd-tree/lib/debian-installer-startup.d/*
	mkdir -p $(GEN)
	gzip -cd $(IN)/initrd.gz > $(GEN)/initrd-preseeded
	cd $(IN)/initrd-tree && find . | cpio -H newc -o --append -F ../../$(GEN)/initrd-preseeded

run:
	$(INTERPRETER) -M $(MACHINE) \
		$(INTERPRETER-ARGS) \
		-device virtio-rng-pci \
		-device virtio-net-pci,netdev=user.0 \
		-drive file=$(INITVM),if=$(HD_TYPE),bus=1,unit=0 \
		-no-reboot \
		-netdev user,ipv4,id=user.0${fwd} \
		-cpu host \
		-m $(MEMSIZE) \
		-usb \
		-smp $(SMP)

run-con:
	$(INTERPRETER) -M $(MACHINE) \
		$(INTERPRETER-ARGS)
		-device virtio-rng-pci \
		-device virtio-net-pci,netdev=user.0 \
		-drive file=$(INITVM),if=$(HD_TYPE),bus=1,unit=0 \
		-no-reboot \
		-netdev user,ipv4,id=user.0${fwd} \
		-cpu host \
		-m $(MEMSIZE) \
		-usb \
		-nographic \
		-smp $(SMP)


run_qemu:
	$(INTERPRETER) -M $(MACHINE) \
		$(INTERPRETER-ARGS) \
		-nographic \
		-monitor unix:qemu-monitor-socket,server,nowait \
		-serial unix:vm-serial-socket,server,nowait \
		-device virtio-rng-pci \
		-device virtio-net-pci,netdev=user.0 \
		-drive file=$(INITVM),if=$(HD_TYPE),bus=1,unit=0 \
		-no-reboot \
		-netdev user,ipv4=on,id=user.0,hostfwd=tcp::7587-:7588${fwd} \
		-cpu host \
		-m $(MEMSIZE) \
		-usb \
		-smp $(SMP)

clean:
	rm -fr $(CLEAN)

distclean: clean
	@echo clean

.PHONY: all clean distclean run run-con
