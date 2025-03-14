# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2024 Linutronix GmbH

try:
    import elbevalidate.pytest
    pytest_plugins = elbevalidate.pytest.plugin
except ModuleNotFoundError as e:
    if e.name != 'guestfs':
        raise
