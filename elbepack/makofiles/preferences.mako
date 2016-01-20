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
<%!
    import textwrap
    from textwrap import dedent
%>
% if prj.has("preference"):
Package: *
Pin: release o=${prj.text("preference")}
Pin-Priority: ${prj.node("preference").et.attrib["pin"]}

% endif
% for pref in prj.et.iter('raw-preference'):
${textwrap.dedent(pref.text).strip()}

% endfor
% for porg in porgs:
Package: ${porg['package']}
Pin: origin ${porg['origin']}
Pin-Priority: ${porg['pin']}

% endfor
% for n in pkgs:
%  if "pin" in n.et.attrib.keys():
Package: ${n.et.text}
Pin: release a=${n.et.attrib["pin"]}
Pin-Priority: 991

%  endif
%  if "version" in n.et.attrib.keys():
Package: ${n.et.text}
Pin: version ${n.et.attrib["version"]}
Pin-Priority: 1001

%  endif
% endfor
