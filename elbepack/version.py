# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2013-2018 Linutronix GmbH

import pathlib
import site
import sys


_filepath = pathlib.Path(__file__)
is_devel = not _filepath.is_relative_to(sys.prefix) and not _filepath.is_relative_to(site.USER_SITE)
elbe_version = '15.6'
elbe_version_debian = elbe_version
if is_devel:
    elbe_version += '.dev0'

elbe_initvm_packagelist = ['python3-elbe-buildenv',
                           'python3-elbe-soap',
                           'python3-elbe-common',
                           'python3-elbe-daemon',
                           'elbe-schema',
                           'python3-elbe-bin']
