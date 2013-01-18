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
# <file system> <mount point>   <type>  <options>       <dump>  <pass>
% for tab in tgt:
	% if tab.has("bydev"):
		% for d in tab:
			% if d.has("source"):
				% if d.has("options"):
${d.text("source")}	${d.text("mountpoint")}	${d.text("fs/type")}	${d.text("options")}	0	0
				% else:
${d.text("source")}	${d.text("mountpoint")}	${d.text("fs/type")}	defaults	0	0
				% endif
			% endif
		% endfor
	% endif
	% if tab.has("bylabel"):
		% for l in tab:
			% if l.has("label"):
				% for mtd in tgt.node("images"):
					% if mtd.has("ubivg"):
						% for ubivg in mtd:
							% for vol in ubivg:
								% if vol.has("label"):
									% if vol.text("label") == l.text("label"):
ubi${mtd.text("nr")}:${l.text("label")}	${l.text("mountpoint")}	${l.text("fs/type")}	defaults	0	0
									% endif
								% endif
							% endfor
						% endfor
					% endif
				% endfor
			% endif
		% endfor
	% endif
% endfor
