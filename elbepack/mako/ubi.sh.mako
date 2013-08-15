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

% if tgt.has("images"):

% for mtd in tgt.node("images"):
% if mtd.has("ubivg"):
% for vol in mtd.node("ubivg"):
% if vol.has("label"):
echo [${vol.text("label")}] >> ${mtd.text("name")}_${mtd.node("ubivg").text("label")}.cfg
echo mode=ubi >> ${mtd.text("name")}_${mtd.node("ubivg").text("label")}.cfg
% if not vol.has("empty"):
% if vol.has("binary"):
echo image=${vol.text("binary")} >> ${mtd.text("name")}_${mtd.node("ubivg").text("label")}.cfg
% else:
echo image=/opt/elbe/${vol.text("label")}.ubifs >> ${mtd.text("name")}_${mtd.node("ubivg").text("label")}.cfg
% endif
% else:
echo image=/tmp/empty >> ${mtd.text("name")}_${mtd.node("ubivg").text("label")}.cfg
% endif
echo vol_type=${vol.text("type")} >> ${mtd.text("name")}_${mtd.node("ubivg").text("label")}.cfg
echo vol_id=${vol.text("id")} >> ${mtd.text("name")}_${mtd.node("ubivg").text("label")}.cfg
echo vol_name=${vol.text("label")} >> ${mtd.text("name")}_${mtd.node("ubivg").text("label")}.cfg
% if vol.text("size") != "remain":
echo vol_size=${vol.text("size")} >> ${mtd.text("name")}_${mtd.node("ubivg").text("label")}.cfg
% endif
% endif
% endfor
% endif
% endfor
% endif
