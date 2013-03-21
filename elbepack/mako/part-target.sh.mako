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

MOUNTCNT=0

echo ""
echo "create target images"
echo "--------------------"
echo ""
echo "================================================================"

<% 
interpreter = prj.text("buildimage/interpreter", default=defs, key="interpreter")
if interpreter == "kvm":
  fdisk_name = "fdisk"
elif interpreter == "qemu-system-ppc":
  fdisk_name = "ddisk"
else:
  fdisk_name = "fdisk"
%>

mkdir -v -p /tmp-mnt

# create and loopback mount hd disk images
% if tgt.has("images"):
%  for hd in tgt.node("images"):
%   if hd.has("partitions"):
<% 
    s=int(hd.text("size"))
    c=(s*1000*1024)/(16*63*512)
%>
dd if=/dev/zero of=/mnt/${hd.text("name")} count=${c} bs=516096c
${fdisk_name} -H 16 -S 63 /mnt/${hd.text("name")} ${"<<"}EOF
%    for part in hd.node("partitions"):
n
p
${part.text("part")}

%     if part.text("size")=="remain":

%     else:
+${part.text("size")}
%     endif
%    endfor
w
EOF

%    for part in hd.node("partitions"):
# TODO use size of last partition to calc new offset
losetup -o32256 /dev/loop$MOUNTCNT
# TODO get mountpoint from fstab
mount -o loop /dev/loop$MOUNTCNT /tmp-mnt/${hd.text("name")}${part.text("part")}
MOUNTCOUNT=$MOUNTCNT+1
%    endfor
# TODO copy files, install grub
%   endif
%  endfor
% endif

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
