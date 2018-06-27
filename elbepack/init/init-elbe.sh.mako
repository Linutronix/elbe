## ELBE - Debian Based Embedded Rootfilesystem Builder
## Copyright (c) 2014-2016 Torben Hohn <torben.hohn@linutronix.de>
## Copyright (c) 2014, 2017 Manuel Traut <manut@linutronix.de>
## Copyright (c) 2016 John Ogness <john.ogness@linutronix.de>
##
## SPDX-License-Identifier: GPL-3.0-or-later
##
#! /bin/sh

# First unset the variables which are set by the debian-installer
unset DEBCONF_REDIR DEBCONF_OLD_FD_BASE MENU
unset DEBIAN_FRONTEND DEBIAN_HAS_FRONTEND debconf_priority
unset TERM_TYPE

# stop confusion /target is buildenv in this context
ln -s /target /buildenv

mkdir -p /buildenv/var/cache/elbe
cp source.xml /buildenv/var/cache/elbe/
cp /etc/apt/apt.conf /buildenv/etc/apt/apt.conf.d/50elbe


% if prj.text('suite') == 'jessie':
ln -s /lib/systemd/system/serial-getty@.service /buildenv/etc/systemd/system/getty.target.wants/serial-getty@ttyS0.service
% endif

% if opt.devel:
   mkdir /buildenv/var/cache/elbe/devel
   tar xj -f elbe-devel.tar.bz2 -C /buildenv/var/cache/elbe/devel
   echo "export PATH=/var/cache/elbe/devel:\$PATH" > /buildenv/etc/profile.d/elbe-devel-path.sh
   sed -i s%/usr/bin/elbe%/var/cache/elbe/devel/elbe% /buildenv/etc/init.d/elbe-daemon
   sed -i s%/usr/bin/elbe%/var/cache/elbe/devel/elbe% /buildenv/lib/systemd/system/elbe-daemon.service
% endif

exit 0
