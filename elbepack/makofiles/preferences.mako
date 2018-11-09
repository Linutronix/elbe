## ELBE - Debian Based Embedded Rootfilesystem Builder
## Copyright (c) 2014, 2017 Manuel Traut <manut@linutronix.de>
## Copyright (c) 2014 Ferdinand Schwenk <ferdinand.schwenk@emtrion.de>
## Copyright (c) 2017 John Ogness <john.ogness@linutronix.de>
##
## SPDX-License-Identifier: GPL-3.0-or-later
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
% if pkgs:
%  for n in pkgs:
%   if "pin" in n.et.attrib.keys():
Package: ${n.et.text}
Pin: release n=${n.et.attrib["pin"]}
Pin-Priority: 991

%   endif
%   if "version" in n.et.attrib.keys():
Package: ${n.et.text}
Pin: version ${n.et.attrib["version"]}
Pin-Priority: 1001

%   endif
%  endfor
% endif
