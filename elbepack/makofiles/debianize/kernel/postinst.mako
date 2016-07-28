#!/bin/sh

set -e

# Pass maintainer script parameters to hook scripts
export DEB_MAINT_PARAMS="$*"

# Tell initramfs builder whether it's wanted
export INITRD=Yes

test -d /etc/kernel/postinst.d && run-parts --arg="${k_version}-${p_name}" --arg="/boot/vmlinuz-${k_version}-${p_name}" /etc/kernel/postinst.d
exit 0
