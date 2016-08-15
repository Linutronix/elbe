#!/usr/bin/make -f

MOD_PATH=`pwd`/debian/tmp
FW_PATH=`pwd`/debian/tmp/lib/firmware
HDR_PATH=`pwd`/debian/tmp/usr
KERNEL_PATH=`pwd`/debian/tmp/boot
DTBS_PATH=`pwd`/debian/tmp/usr/lib/linux-image-${k_version}-${p_name}

MAKE_OPTS= \
ARCH=${k_arch} \
CROSS_COMPILE=${cross_compile} \
KERNELRELEASE=${k_version}-${p_name} \
LOADADDR=${loadaddr} \
INSTALL_MOD_PATH=$(MOD_PATH) \
INSTALL_FW_PATH=$(FW_PATH) \
INSTALL_HDR_PATH=$(HDR_PATH) \
INSTALL_PATH=$(KERNEL_PATH) \
INSTALL_DTBS_PATH=$(DTBS_PATH) \
O=debian/build

#export DH_VERBOSE=1

override_dh_auto_clean:
	mkdir -p debian/build
	rm -f debian/files debian/tmp
	make $(MAKE_OPTS) clean

override_dh_auto_configure:
	mkdir -p debian/build
	make $(MAKE_OPTS) ${defconfig}

override_dh_auto_build:
	rm -rf include/config
	make -j`nproc` $(MAKE_OPTS) ${imgtype} modules
	test ${k_arch} = arm && make -j`nproc` $(MAKE_OPTS) dtbs || true

override_dh_auto_install:
	mkdir -p $(MOD_PATH) $(FW_PATH) $(HDR_PATH) $(KERNEL_PATH) $(DTBS_PATH)
	make $(MAKE_OPTS) install
	make $(MAKE_OPTS) INSTALL_MOD_STRIP=1 modules_install
	make $(MAKE_OPTS) firmware_install
	make $(MAKE_OPTS) headers_install
	test ${k_arch} = arm && make $(MAKE_OPTS) dtbs_install || true

%%:
	dh $@
