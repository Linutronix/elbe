#!/usr/bin/make -f

MOD_PATH=`pwd`/debian/tmp/lib/modules/${k_version}
FW_PATH=`pwd`/debian/tmp/lib/firmware
HDR_PATH=`pwd`/debian/tmp/usr/include
KERNEL_PATH=`pwd`/debian/tmp/boot

MAKE_OPTS= \
ARCH=${k_arch} \
CROSS_COMPILE=${cross_compile} \
KBUILD_DEBARCH=${k_debarch} \
KDEB_PKGVERSION=${k_debversion} \
KERNELRELEASE=${k_name}-${k_version} \
LOADADDR=${loadaddr} \
O=debian/build \
INSTALL_MOD_PATH=$(MOD_PATH) \
INSTALL_FW_PATH=$(FW_PATH) \
INSTALL_HDR_PATH=$(HDR_PATH) \
INSTALL_PATH=$(KERNEL_PATH)

ifneq (,$(filter parallel=%,$(DEB_BUILD_OPTIONS)))
       NUMJOBS = $(patsubst parallel=%,%,$(filter parallel=%,$(DEB_BUILD_OPTIONS)))
       MAKE_OPTS += -j$(NUMJOBS)
endif

clean:
	mkdir -p $(MOD_PATH) $(FW_PATH) $(HDR_PATH) $(KERNEL_PATH)
	rm -f debian/files
	rm -rf debian/tmp
	make $(MAKE_OPTS) clean

build-arch:
	mkdir -p debian/build debian/tmp
	make $(MAKE_OPTS) ${defconfig}
	make $(MAKE_OPTS) ${imgtype} modules

build-indep: ;

build: build-arch build-indep

binary: binary-arch binary-indep

binary-arch:
	make $(MAKE_OPTS) install
	make $(MAKE_OPTS) modules_install
	make $(MAKE_OPTS) firmware_install
	make $(MAKE_OPTS) headers_install

binary-indep: ;
