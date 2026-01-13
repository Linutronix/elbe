# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2013-2018 Linutronix GmbH

import pathlib
import site
import sys


def _is_devel(p):
    if p.is_relative_to(sys.prefix):
        return False

    if site.USER_SITE is not None and p.is_relative_to(site.USER_SITE):
        return False

    return True


_filepath = pathlib.Path(__file__)
is_devel = _is_devel(_filepath)
elbe_version = '15.8'
elbe_version_debian = elbe_version

elbe_initvm_packagelist = ['python3-elbe-buildenv',
                           'python3-elbe-soap',
                           'python3-elbe-common',
                           'python3-elbe-daemon',
                           'elbe-schema',
                           'python3-elbe-bin']
