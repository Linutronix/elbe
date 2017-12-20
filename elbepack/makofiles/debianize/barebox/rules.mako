## ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (c) 2017 Torben Hohn <torben.hohn@linutronix.de>
# Copyright (c) 2017 Manuel Traut <manut@linutronix.de>
##
## SPDX-License-Identifier: GPL-3.0-or-later
##
#!/usr/bin/make -f

BOOT_PATH=`pwd`/debian/tmp/boot
TOOL_PATH=`pwd`/debian/tmp/usr/bin

MAKE_OPTS= \
ARCH=${k_arch} \
CROSS_COMPILE=${cross_compile} \
KERNELRELEASE=${k_version}-${p_name} \
O=debian/build

#export DH_VERBOSE=1
export LDFLAGS=

override_dh_auto_clean:
	mkdir -p debian/build
	rm -f debian/files
	rm -rf debian/tmp
	make $(MAKE_OPTS) clean

override_dh_auto_configure:
	mkdir -p debian/build
	make $(MAKE_OPTS) ${defconfig}

override_dh_auto_build:
	rm -rf include/config
	make -j`nproc` $(MAKE_OPTS)

override_dh_auto_install:
	mkdir -p $(TOOL_PATH) $(BOOT_PATH)
	cp debian/build/images/${imgname} $(BOOT_PATH)
	-cp debian/build/scripts/bareboxcrc32-target $(TOOL_PATH)/bareboxcrc32
	-cp debian/build/scripts/bareboxenv-target $(TOOL_PATH)/bareboxenv

%%:
	dh $@
