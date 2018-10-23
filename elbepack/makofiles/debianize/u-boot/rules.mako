## ELBE - Debian Based Embedded Rootfilesystem Builder
## Copyright (c) 2018 Philipp Rosenberger <p.rosenberger@linutronix.de>
##
## SPDX-License-Identifier: GPL-3.0-or-later
##
#!/usr/bin/make -f

BOOT_PATH=`pwd`/debian/tmp/boot
TOOL_PATH=`pwd`/debian/tmp/usr/bin

BUILD_DIR=`pwd`/debian/build

MAKE_OPTS= \
ARCH=${k_arch} \
CROSS_COMPILE=${cross_compile} \
KERNELRELEASE=${k_version}-${p_name} \
O=$(BUILD_DIR)

#export DH_VERBOSE=1
export LDFLAGS=

override_dh_auto_test:
	# skip tests.

override_dh_auto_clean:
	mkdir -p $(BUILD_DIR)
	rm -f debian/files
	rm -rf debian/tmp
	make $(MAKE_OPTS) clean

override_dh_auto_configure:
	mkdir -p $(BUILD_DIR)
	make $(MAKE_OPTS) ${defconfig}

override_dh_auto_build:
	make -j`nproc` $(MAKE_OPTS)
	make -j`nproc` $(MAKE_OPTS) ${envtools}
	make -j`nproc` $(MAKE_OPTS) CROSS_BUILD_TOOLS=y tools-only

override_dh_auto_install:
	mkdir -p $(TOOL_PATH) $(BOOT_PATH)
	cp $(BUILD_DIR)/${imgname} $(BOOT_PATH)
	-cp $(BUILD_DIR)/tools/dumpimage $(TOOL_PATH)
	-cp $(BUILD_DIR)/tools/mkenvimage $(TOOL_PATH)
	-cp $(BUILD_DIR)/tools/mkimage $(TOOL_PATH)
	-cp $(BUILD_DIR)/tools/env/fw_printenv $(TOOL_PATH)

%%:
	dh $@
