## ELBE - Debian Based Embedded Rootfilesystem Builder
## Copyright (c) 2018 Philipp Rosenberger <p.rosenberger@linutronix.de>
##
## SPDX-License-Identifier: GPL-3.0-or-later
##
Source: u-boot-${p_name}-${k_version}
Section: admin
Priority: optional
Maintainer: ${m_name} <${m_mail}>
Build-Depends:
 debhelper (>= 9),
 bc,
 bison,
 device-tree-compiler,
 debhelper,
 flex,
 lzop:native,
Standards-Version: 3.8.4
Homepage: http://www.denx.de/wiki/U-Boot/

Package: u-boot-image-${p_name}-${k_version}
Provides: u-boot-image
Architecture: ${p_arch}
Description: A boot loader for embedded systems
 Das U-Boot is a cross-platform bootloader for embedded systems, used as the default boot loader by several board
 vendors.  It is intended to be easy to port and to debug, and runs on many supported architectures, including PPC,
 ARM, MIPS, x86, m68k, NIOS, and Microblaze.

Package: u-boot-tools-${p_name}-${k_version}
Provides: u-boot-tools
Architecture: ${p_arch}
Description: companion tools for Das U-Boot bootloader
 This package includes the mkimage program, which allows generation of U-Boot
 images in various formats, and the fw_printenv and fw_setenv programs to read
 and modify U-Boot's environment.
