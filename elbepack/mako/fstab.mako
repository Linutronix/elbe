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
<%

from elbepack.fstab import fstabentry

if tgt.has("fstab"):
    fslabel = {}
    for fs in tgt.node("fstab"):
	if fs.tag != "bylabel":
	    continue

	fslabel[fs.text("label")] = fstabentry(fs)

def get_mtdnum(label):
	if not tgt.has("images"):
		raise Exception( "No images tag in target" )

	for i in tgt.node("images"):
		if i.tag != "mtd":
			continue

		if not i.has("ubivg"):
			continue

		for v in i.node("ubivg"):
			if v.tag != "ubi":
				continue

			if v.text("label") == label:
				return i.text("nr")

	raise Exception( "No ubi volume with label " + label + " found" )

def get_devicelabel( node ):
	if node.text("fs/type") == "ubifs":
		return "ubi" + get_mtdnum(node.text("label")) + ":" + node.text("label")
	else:
		return "LABEL=" + node.text("label")


%>
# <file system> <mount point>   <type>  <options>       <dump>  <pass>
% if tgt.has("fstab"):
	% for d in tgt.node("fstab"):
		% if d.tag == "bydev":
${d.text("source")}	${d.text("mountpoint")}	${d.text("fs/type")}	${d.text("options", default="defaults")}	0	0
		% endif
		% if d.tag == "bylabel":
${get_devicelabel(d)}	${d.text("mountpoint")}	${d.text("fs/type")}	${d.text("options", default="defaults")}	0	0
		% endif
	% endfor
% endif
