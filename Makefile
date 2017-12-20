# ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (c) 2014-2017 Manuel Traut <manut@linutronix.de>
#
# SPDX-License-Identifier: GPL-3.0-or-later

all:
	./test/testdeb.sh
	dpkg-buildpackage
	lintian
	cd contrib/debathena-transform-lighttpd && \
		dpkg-buildpackage -uc -us && \
		lintian && \
		mv ../debathena*.* ../../../
