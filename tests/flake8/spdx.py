# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2024 Linutronix GmbH

class SPDXChecker:
    name = 'spdx'
    version = '0.0.0'

    def __init__(self, tree, lines):
        self.lines = lines

    def run(self):
        lines = list(self.lines)

        if not lines:
            return

        if lines[0].startswith('#!'):
            lines.pop(0)

            if lines[0] == '\n':
                lines.pop(0)

        if len(lines) < 4 or \
                lines[0] != '# ELBE - Debian Based Embedded Rootfilesystem Builder\n' or \
                lines[1] != '# SPDX-License-Identifier: GPL-3.0-or-later\n' or \
                not lines[2].startswith('# SPDX-FileCopyrightText: '):

            yield 1, 0, 'SP1 invalid copyright header', type(self)
