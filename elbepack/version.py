# ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (c) 2013, 2017-2018 Manuel Traut <manut@linutronix.de>
# Copyright (c) 2015 Torben Hohn <torbenh@linutronix.de>
#
# SPDX-License-Identifier: GPL-3.0-or-later


from elbepack.directories import pack_dir

elbe_version = "13.2"

elbe_initvm_packagelist = ['python3-elbe-buildenv',
                           'python3-elbe-soap',
                           'python3-elbe-common',
                           'python3-elbe-daemon',
                           'elbe-schema',
                           'python3-elbe-bin']

if pack_dir.startswith('/usr/lib/python'):
    is_devel = False
else:
    is_devel = True
