## ELBE - Debian Based Embedded Rootfilesystem Builder
## Copyright (c) 2017 Torben Hohn <torben.hohn@linutronix.de>
## Copyright (c) 2017 Manuel Traut <manut@linutronix.de>
##
## SPDX-License-Identifier: GPL-3.0-or-later
##
#!/usr/bin/make -f

<%
items = imgname.split(' ')
img_name_aux = ''
img_name = items[0]
if len(items) > 1:
    img_name_aux = items[1]

items = defconfig.split(' ')
def_config_aux = ''
def_config = items[0]
if len(items) > 1:
    def_config_aux = items[1]
%>

BOOT_PATH=`pwd`/debian/tmp/boot
TOOL_PATH=`pwd`/debian/tmp/usr/bin

MAKE_OPTS= \
ARCH=${k_arch} \
CROSS_COMPILE=${cross_compile} \
KERNELRELEASE=${k_version}-${p_name}

#export DH_VERBOSE=1
export LDFLAGS=

override_dh_auto_clean:
	mkdir -p debian/build
% if def_config_aux:
	mkdir -p debian/build-aux
% endif
	rm -f debian/files
	rm -rf debian/tmp
	make $(MAKE_OPTS) O=debian/build clean
% if def_config_aux:
	make $(MAKE_OPTS) O=debian/build-aux clean
% endif

override_dh_auto_configure:
	mkdir -p debian/build
	make $(MAKE_OPTS) O=debian/build ${def_config}
% if def_config_aux:
	mkdir -p debian/build-aux
	make $(MAKE_OPTS) O=debian/build-aux ${def_config_aux}
% endif

override_dh_auto_build:
	rm -rf include/config
	make -j`nproc` $(MAKE_OPTS) O=debian/build
% if def_config_aux:
	make -j`nproc` $(MAKE_OPTS) O=debian/build-aux
% endif

override_dh_auto_test:

override_dh_auto_install:
	mkdir -p $(TOOL_PATH) $(BOOT_PATH)
	cp debian/build/images/${img_name} $(BOOT_PATH)
% if img_name_aux:
	cp debian/build-aux/images/${img_name_aux} $(BOOT_PATH)
% endif
	-cp debian/build/scripts/bareboxcrc32-target $(TOOL_PATH)/bareboxcrc32
	-cp debian/build/scripts/bareboxenv-target $(TOOL_PATH)/bareboxenv

%%:
	dh $@
