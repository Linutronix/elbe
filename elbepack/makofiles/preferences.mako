## ELBE - Debian Based Embedded Rootfilesystem Builder
## SPDX-License-Identifier: GPL-3.0-or-later
## SPDX-FileCopyrightText: 2014, 2017 Linutronix GmbH
## SPDX-FileCopyrightText: 2014 Ferdinand Schwenk <ferdinand.schwenk@emtrion.de>

<%!
    import textwrap
    from textwrap import dedent

    def pkg_properties_specified(attrib):
        """Check if any package pinning properties are provided."""
        for key in ['version',
                    'origin',
                    'release-archive',
                    'release-component',
                    'release-label',
                    'release-name',
                    'release-origin',
                    'release-version']:
            if key in attrib:
                return True
        return False

    def generate_pin_text(attrib):
        """Generate the package pinning properties based on the provided attributes."""
        # return early as the attributes are mutually exclusive
        if 'version' in attrib:
            return f'Pin: version {attrib["version"]}'

        if 'origin' in attrib:
            return f'Pin: origin "{attrib["origin"]}"'

        opts = {
            'a': attrib.get('release-archive'),
            'c': attrib.get('release-component'),
            'l': attrib.get('release-label'),
            'n': attrib.get('release-name'),
            'o': attrib.get('release-origin'),
            'v': attrib.get('release-version'),
        }
        release_opts = ', '.join([f'{k}={v}' for k, v in opts.items() if v is not None])
        if release_opts:
            return f'Pin: release {release_opts}'

        raise RuntimeError('Unknown pinning properties provided')
%>
% if prj.has('preference'):
Package: *
Pin: release o=${prj.text('preference')}
Pin-Priority: ${prj.node('preference').et.attrib['pin']}

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
%   if pkg_properties_specified(n.et.attrib):
Package: ${n.et.text}
${generate_pin_text(n.et.attrib)}
Pin-Priority: 1001

%   endif
%  endfor
% endif
