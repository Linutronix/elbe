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

# used by ubi.cfg for ubi volumes tagged as empty
echo EMPTY > /tmp/empty

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


% if tgt.has("images"):
# add binaries like kernel / uboot to files to extract list
	% for mtd in tgt.node("images"):
		% if mtd.has("ubivg"):
			% for vol in mtd.node("ubivg"):
				% if vol.has("binary"):
echo "${vol.text("binary")}" >> /opt/elbe/files-to-extract
				% endif
			% endfor
		% endif
	% endfor
% endif


