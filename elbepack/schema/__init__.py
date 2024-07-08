# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2024 Linutronix GmbH

import importlib.resources


def xml_schema_file(name):
    return importlib.resources.files(__name__).joinpath(name).open('r')
