# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2013-2018 Linutronix GmbH

import pathlib
import sys

elbe_version = '15.0.alpha1'

elbe_initvm_packagelist = ['python3-elbe-buildenv',
                           'python3-elbe-soap',
                           'python3-elbe-common',
                           'python3-elbe-daemon',
                           'elbe-schema',
                           'python3-elbe-bin']

is_devel = not pathlib.Path(__file__).is_relative_to(sys.prefix)
