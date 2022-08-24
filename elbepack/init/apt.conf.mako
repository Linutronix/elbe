## ELBE - Debian Based Embedded Rootfilesystem Builder
## SPDX-License-Identifier: GPL-3.0-or-later
## SPDX-FileCopyrightText: 2014, 2017 Linutronix GmbH
##
%if http_proxy:
Acquire {
	http {
		Proxy "${http_proxy}";
		Proxy::10.0.2.2 "DIRECT";
	}
}
%endif
