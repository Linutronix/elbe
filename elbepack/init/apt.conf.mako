## ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (c) 2014, 2017 Manuel Traut <manut@linutronix.de>
##
## SPDX-License-Identifier: GPL-3.0-or-later
##
%if http_proxy:
Acquire {
	http {
		Proxy "${http_proxy}";
		Proxy::10.0.2.2 "DIRECT";
	}
}
%endif
