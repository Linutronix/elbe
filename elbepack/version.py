# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2013-2018 Linutronix GmbH

import pathlib
import sys


is_devel = not pathlib.Path(__file__).is_relative_to(sys.prefix)
elbe_version_base = '15.0a4'
elbe_version = elbe_version_base
if is_devel:
    elbe_version += '.dev0'

elbe_initvm_packagelist = ['python3-elbe-buildenv',
                           'python3-elbe-soap',
                           'python3-elbe-common',
                           'python3-elbe-daemon',
                           'elbe-schema',
                           'python3-elbe-bin']
