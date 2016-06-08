#!/usr/bin/make -f

MAKE_OPTS= \
ARCH=${k_arch} \
CROSS_COMPILE=${cross_compile} \
KBUILD_DEBARCH=${k_debarch} \
KDEB_PKGVERSION=${k_debversion} \
KERNELRELEASE=${k_name}-${k_version} \
LOADADDR=${loadaddr} \
O=debian/build \
INSTALL_MOD_PATH=`pwd`/debian/tmp \
INSTALL_FW_PATH=`pwd`/debian/tmp \
INSTALL_HDR_PATH=`pwd`/debian/tmp \
INSTALL_PATH=`pwd`/debian/tmp

ifneq (,$(filter parallel=%,$(DEB_BUILD_OPTIONS)))
       NUMJOBS = $(patsubst parallel=%,%,$(filter parallel=%,$(DEB_BUILD_OPTIONS)))
       MAKE_OPTS += -j$(NUMJOBS)
endif

clean:
	mkdir -p debian/build
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
