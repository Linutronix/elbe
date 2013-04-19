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

ELBEFILES="/passwd.cfg /preseed.cfg /common.cfg /custom-preseed.cfg /pkg-list \
		/finetuning.sh /post-inst.sh /Release.bin \
		/create-target-rfs.sh /Release.src /part-target.sh  \
		/preferences /ubi.cfg /dump.py /treeutils.py /source.xml \
		/pkg-selections /print_licence.sh /fstab /mkcdrom.sh /hdimg.py"

%if xml.has("archive"):
ELBEFILES="$ELBEFILES /archive.tar.bz2"
%endif

# stop confusion /target is buildenv in this context
ln -s /target /buildenv

mkdir -p /buildenv/opt/elbe
cp $ELBEFILES /buildenv/opt/elbe/

mkdir -p /buildenv/var/log
cp /var/log/syslog /buildenv/var/log	

%if not opt.skip_cds:
mkdir -p /buildenv/repo/binary
mkdir -p /buildenv/repo/source
cp /Release.bin /buildenv/repo/binary/Release
cp /Release.src /buildenv/repo/source/Release
%endif

exit 0
