## ELBE - Debian Based Embedded Rootfilesystem Builder
## Copyright (c) 2016 John Ogness <john.ogness@linutronix.de>
## Copyright (c) 2017 Manuel Traut <manut@linutronix.de>
##
## SPDX-License-Identifier: GPL-3.0-or-later
##
#!/bin/sh

set -e

# Pass maintainer script parameters to hook scripts
export DEB_MAINT_PARAMS="$*"

# Tell initramfs builder whether it's wanted
export INITRD=Yes

test -d /etc/kernel/preinst.d && run-parts --arg="${k_version}-${p_name}" --arg="/boot/vmlinuz-${k_version}-${p_name}" /etc/kernel/preinst.d
exit 0
