## ELBE - Debian Based Embedded Rootfilesystem Builder
## Copyright (c) 2014-2016 Torben Hohn <torben.hohn@linutronix.de>
## Copyright (c) 2014, 2017 Manuel Traut <manut@linutronix.de>
## Copyright (c) 2016 John Ogness <john.ogness@linutronix.de>
##
## SPDX-License-Identifier: GPL-3.0-or-later
##
#! /bin/sh
<%
elbe_exe = '/usr/bin/elbe'

if opt.devel:
    elbe_exe = '/var/cache/elbe/devel/elbe'

buildrepo_opts = ''

if not opt.build_bin:
  buildrepo_opts += '--skip-build-bin'

if not opt.build_sources:
  buildrepo_opts += '--skip-build-source'

nicmac = prj.text('buildimage/NIC/MAC', default=defs, key='nicmac')
%>

# First unset the variables which are set by the debian-installer
unset DEBCONF_REDIR DEBCONF_OLD_FD_BASE MENU
unset DEBIAN_FRONTEND DEBIAN_HAS_FRONTEND debconf_priority
unset TERM_TYPE

# stop confusion /target is buildenv in this context
ln -s /target /buildenv

mkdir -p /buildenv/var/cache/elbe
cp source.xml /buildenv/var/cache/elbe/
cp /etc/apt/apt.conf /buildenv/etc/apt/apt.conf.d/50elbe

ln -s /lib/systemd/system/serial-getty@.service /buildenv/etc/systemd/system/getty.target.wants/serial-getty@ttyS0.service

mkdir /buildenv/var/cache/elbe/installer
cp initrd-cdrom.gz /buildenv/var/cache/elbe/installer
cp vmlinuz /buildenv/var/cache/elbe/installer

cat <<EOF > /buildenv/etc/systemd/network/10-host.link
[Match]
MACAddress=${nicmac}

[Link]
NamePolicy=
Name=host0
EOF

cat <<EOF > /buildenv/etc/network/interfaces.d/host0
# The primary network interface
allow-hotplug host0
iface host0 inet dhcp
EOF

in-target update-initramfs -u

% if opt.devel:
   mkdir /buildenv/var/cache/elbe/devel
   tar xj -f elbe-devel.tar.bz2 -C /buildenv/var/cache/elbe/devel
   echo "export PATH=/var/cache/elbe/devel:\$PATH" > /buildenv/etc/profile.d/elbe-devel-path.sh
   sed -i s%/usr/bin/elbe%/var/cache/elbe/devel/elbe% /buildenv/etc/init.d/python3-elbe-daemon
   sed -i s%/usr/bin/elbe%/var/cache/elbe/devel/elbe% /buildenv/lib/systemd/system/python3-elbe-daemon.service
% endif

# since elbe fetch_initvm_pkgs generates repo keys,
# we need entropy in the target

in-target haveged

% if prj.has("mirror/cdrom"):
  in-target ${elbe_exe} fetch_initvm_pkgs ${buildrepo_opts} --cdrom-device /dev/sr0 --cdrom-mount-path /media/cdrom0 /var/cache/elbe/source.xml
% else:
  in-target ${elbe_exe} fetch_initvm_pkgs ${buildrepo_opts} /var/cache/elbe/source.xml
% endif

% if prj.has("finetuning"):
%   for node in prj.all("./finetuning/"):
%     if "command" == node.tag:
	cat <<ELBE_INITVM_FINETUNING_EOF > /buildenv/tmp/elbe-initvm
${"\n".join(line.lstrip(" \t") for line in node.et.text.strip("\n").splitlines())}
ELBE_INITVM_FINETUNING_EOF
	in-target sh /tmp/elbe-initvm
%     endif
%   endfor
% endif

exit 0
