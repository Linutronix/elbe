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
% if tgt.has("images"):

% for mtd in tgt.node("images"):
% if mtd.has("ubivg"):
% for vol in mtd.node("ubivg"):
% if vol.has("label"):
[${vol.text("label")}]
mode=ubi
% if vol.has("binary"):
image=${vol.text("binary")}
% else:
image=/opt/elbe/${vol.text("label")}.ubifs
% endif
vol_type=${vol.text("type")}
vol_id=${vol.text("id")}
vol_name=${vol.text("label")}
% if vol.text("size") != "remain":
vol_size=${vol.text("size")}
% endif

% endif
% endfor
% endif
% endfor

% endif
