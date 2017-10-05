#!/usr/bin/make -f

PWD:=$(shell pwd)
REL:=${k_version}-${p_name}

DEB_DIR:=$(PWD)/debian
TMP_DIR:=$(DEB_DIR)/tmp
BUILD_DIR:=$(DEB_DIR)/build

MOD_PATH:=$(TMP_DIR)
FW_PATH:=$(TMP_DIR)/lib/firmware
KERNEL_PATH:=$(TMP_DIR)/boot
HDR_PATH:=$(TMP_DIR)/usr
KERNEL_HDR_PATH:=$(TMP_DIR)/usr/src/linux-headers-$(REL)
DTBS_PATH:=$(TMP_DIR)/usr/lib/linux-image-$(REL)

ARCH:=${k_arch}
SRCARCH:=$(ARCH)
# Additional ARCH settings for x86
ifeq ($(ARCH),i386)
        SRCARCH := x86
endif
ifeq ($(ARCH),x86_64)
        SRCARCH := x86
endif

MAKE_OPTS= \
ARCH=$(ARCH) \
CROSS_COMPILE=$(CROSS_COMPILE) \
KERNELRELEASE=$(REL) \
LOADADDR=${loadaddr} \
INSTALL_MOD_PATH=$(MOD_PATH) \
INSTALL_FW_PATH=$(FW_PATH) \
INSTALL_HDR_PATH=$(HDR_PATH) \
INSTALL_PATH=$(KERNEL_PATH) \
INSTALL_DTBS_PATH=$(DTBS_PATH) \
O=$(BUILD_DIR)

ifneq (,$(filter parallel=%,$(DEB_BUILD_OPTIONS)))
    NUMJOBS = $(patsubst parallel=%,%,$(filter parallel=%,$(DEB_BUILD_OPTIONS)))
    MAKE_OPTS += -j$(NUMJOBS)
endif

#export DH_VERBOSE=1

override_dh_auto_clean:
	mkdir -p debian/build
	rm -f debian/files
	rm -rf debian/tmp
	$(MAKE) $(MAKE_OPTS) clean

override_dh_auto_configure:
	mkdir -p debian/build
	$(MAKE) $(MAKE_OPTS) ${defconfig}

override_dh_auto_build:
	rm -rf include/config
	$(MAKE) $(MAKE_OPTS) ${imgtype} modules
	(test ${k_arch} = arm || test ${k_arch} = arm64) && make -j`nproc` $(MAKE_OPTS) dtbs || true

override_dh_auto_install:
	mkdir -p $(MOD_PATH) $(FW_PATH) $(HDR_PATH) $(KERNEL_PATH) $(DTBS_PATH)
	$(MAKE) $(MAKE_OPTS) ${imgtype_install}
	$(MAKE) $(MAKE_OPTS) INSTALL_MOD_STRIP=1 modules_install
	$(MAKE) $(MAKE_OPTS) firmware_install
	$(MAKE) $(MAKE_OPTS) headers_install
	(test ${k_arch} = arm || test ${k_arch} = arm64) && make $(MAKE_OPTS) dtbs_install || true
	# Build kernel header package
	rm -f "$(TMP_DIR)/lib/modules/$(REL)/build" "$(TMP_DIR)/lib/modules/$(REL)/source"
	find . -name Makefile\* -o -name Kconfig\* -o -name \*.pl > $(DEB_DIR)/hdrsrcfiles
	find arch/*/include include scripts -type f >> $(DEB_DIR)/hdrsrcfiles
	find arch/$(SRCARCH) -name module.lds -o -name Kbuild.platforms -o -name Platform >> $(DEB_DIR)/hdrsrcfiles
	find `find arch/$(SRCARCH) -name include -o -name scripts -type d` -type f >> $(DEB_DIR)/hdrsrcfiles
	if grep -q '^CONFIG_STACK_VALIDATION=y' $(BUILD_DIR)/.config ; then \
		(cd $(BUILD_DIR); find tools/objtool -type f -executable) >> $(DEB_DIR)/hdrobjfiles ; \
	fi
	(cd $(BUILD_DIR); find arch/$(SRCARCH)/include Module.symvers include scripts -type f) >> $(DEB_DIR)/hdrobjfiles
	if grep -q '^CONFIG_GCC_PLUGINS=y' $(BUILD_DIR)/.config ; then \
			(cd $(BUILD_DIR); find scripts/gcc-plugins -name \*.so -o -name gcc-common.h) >> $(DEB_DIR)/hdrobjfiles ; \
	fi
	mkdir -p "$(KERNEL_HDR_PATH)"
	tar -c -f - -T - < "$(DEB_DIR)/hdrsrcfiles" | (cd $(KERNEL_HDR_PATH); tar -xf -)
	(cd $(BUILD_DIR); tar -c -f - -T -) < "$(DEB_DIR)/hdrobjfiles" | (cd $(KERNEL_HDR_PATH); tar -xf -)
	(cd $(BUILD_DIR); cp $(BUILD_DIR)/.config $(KERNEL_HDR_PATH)/.config) # copy .config manually to be where it's expected to be
	ln -sf "/usr/src/linux-headers-$(REL)" "$(TMP_DIR)/lib/modules/$(REL)/build"
	rm -f "$(DEB_DIR)/hdrsrcfiles" "$(DEB_DIR)/hdrobjfiles"

%%:
	dh $@
