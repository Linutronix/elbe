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
#!/bin/sh

echo ""
echo "create target images"
echo "--------------------"
echo ""
echo "================================================================"

cd /opt/elbe

mkdir -v -p /tmp-mnt


echo "================================================================"
echo ""

python /opt/elbe/hdimg.py --directory /tmp-mnt /opt/elbe/source.xml

echo ""
echo "================================================================"

cp -av /target/* /tmp-mnt

echo "================================================================"
echo ""

python /opt/elbe/hdimg.py --directory /tmp-mnt --umount /opt/elbe/source.xml

echo ""
echo "ubi stuff"
echo "---------"
echo ""
echo "================================================================"

% for tab in tgt:
% if tab.has("bylabel"):
% for l in tab:
% if l.has("label"):

% if l.text("fs/type") == "ubifs":
# create ubifs images according to fstab
mkdir -v -p /target${l.text("mountpoint")}
echo "create ${l.text("label")}.ubifs from: /target${l.text("mountpoint")}"
echo "/opt/elbe/${l.text("label")}.ubifs" >> /opt/elbe/files-to-extract
mkfs.ubifs -r /target${l.text("mountpoint")} \
	-o /opt/elbe/${l.text("label")}.ubifs \
% for mtd in tgt.node("images"):
% if mtd.has("ubivg"):
% for ubivg in mtd:
% for vol in ubivg:
% if vol.has("label"):
% if vol.text("label") == l.text("label"):
	-m ${ubivg.text("miniosize")} \
	-e ${ubivg.text("logicaleraseblocksize")} \
	-c ${ubivg.text("maxlogicaleraseblockcount")}
% endif
% endif
% endfor
% endfor
% endif
% endfor
% endif

# move files away that they are not included in other images
mkdir -v -p /tmp/mkfsdone${l.text("mountpoint")}
mv -v /target${l.text("mountpoint")}/* /tmp/mkfsdone${l.text("mountpoint")}/

% endif
% endfor
% endif
% endfor

# move files back
mv -v /tmp/mkfsdone/* /target/

% if tgt.has("images"):
# add binaries like kernel / uboot to files to extract list
	% for mtd in tgt.node("images"):
		% if mtd.has("ubivg"):
			% for vol in ubivg:
				% if vol.has("binary"):
echo "${vol.text("binary")}" >> /opt/elbe/files-to-extract
				% endif
			% endfor
		% endif
	% endfor
% endif

cd /opt/elbe

% if tgt.has("images"):
%  for mtd in tgt.node("images"):
%   if mtd.has("ubivg"):
%    for ubivg in mtd:
%     if ubivg.has("physicaleraseblocksize"):
echo "create ubi image: ${mtd.text("name")}"
ubinize \
%       if ubivg.has("subpagesize"):
 	       -s ${ubivg.text("subpagesize")} \
%       endif
	-o ${mtd.text("name")} \
	-p ${ubivg.text("physicaleraseblocksize")} \
	-m ${ubivg.text("miniosize")} \
	/opt/elbe/ubi.cfg
echo "/opt/elbe/${mtd.text("name")}" >> /opt/elbe/files-to-extract
%     endif
%    endfor
%   endif
%  endfor
% endif

echo "================================================================"
echo ""
