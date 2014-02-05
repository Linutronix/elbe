## ELBE - Debian Based Embedded Rootfilesystem Builder
## Copyright (C) 2013  Linutronix GmbH
##
## This file is part of ELBE.
##
## ELBE is free software: you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation, either version 3 of the License, or
## (at your option) any later version.
##
## ELBE is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.
##
## You should have received a copy of the GNU General Public License
## along with ELBE.  If not, see <http://www.gnu.org/licenses/>.
##
#! /bin/sh

# stop confusion /target is buildenv in this context
ln -s /target /buildenv

mkdir -p /buildenv/opt/elbe
cp source.xml /buildenv/opt/elbe/

mkdir -p /buildenv/dev
mount -o bind /dev /buildenv/dev

mkdir -p /buildenv/sys
mount -o bind /sys /buildenv/sys

mkdir -p /buildenv/proc
mount -o bind /proc /buildenv/proc

chroot /buildenv elbe buildchroot \
% if opt.skip_validation:
  --skip-validation \
% endif
% if opt.skip_cds:
  --skip-cdrom \
% endif
% if opt.buildsources:
  --build-sources \
% endif
% if opt.buildtype:
  --buildtype=${buildtype} \
% endif
  -t /opt/elbe/build \
  -o /opt/elbe/elbe-report.log \
  /opt/elbe/source.xml

umount /buildenv/proc /buildenv/sys /buildenv/dev

exit 0
