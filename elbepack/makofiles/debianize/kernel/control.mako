## ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (c) 2016-2017 Manuel Traut <manut@linutronix.de>
# Copyright (c) 2016 John Ogness <john.ogness@linutronix.de>
# Copyright (c) 2017 Philipp Rosenberger <p.rosenberger@linutronix.de>
##
## SPDX-License-Identifier: GPL-3.0-or-later
##
Source: linux-${p_name}-${k_version}
Section: kernel
Priority: optional
Maintainer: ${m_name} <${m_mail}>
Build-Depends: debhelper (>= 9), bc
Standards-Version: 3.8.4
Homepage: http://www.kernel.org/

Package: linux-image-${p_name}-${k_version}
Depends: kmod | module-init-tools, linux-base (>= 3~), debconf (>= 0.5) | debconf-2.0, initramfs-tools (>= 0.99~) | linux-initramfs-tool, busybox
Pre-Depends: debconf | debconf-2.0
Provides: linux-image, linux-image-2.6
Architecture: ${p_arch}
Description: Linux kernel, version ${p_name} ${k_version}
 This package contains the Linux kernel, modules and corresponding other
 files

Package: linux-headers-${p_name}-${k_version}
Provides: linux-headers, linux-headers-2.6
Architecture: ${p_arch}
Description: Linux kernel headers
 This package provides kernel header files
 .
 This is useful for people who need to build external modules

Package: linux-libc-dev-${p_name}-${k_version}
Provides: linux-libc-dev, linux-kernel-headers, linux-headers-2.6
Replaces: linux-libc-dev
Architecture: ${p_arch}
Description: Linux support headers for userspace development
 This package provides userspaces headers from the Linux kernel. These headers
 are used by the installed headers for GNU glibc and other system libraries.
