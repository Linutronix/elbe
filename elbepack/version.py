# ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (c) 2013, 2017-2018 Manuel Traut <manut@linutronix.de>
# Copyright (c) 2015 Torben Hohn <torbenh@linutronix.de>
#
# SPDX-License-Identifier: GPL-3.0-or-later


from elbepack.directories import pack_dir

elbe_version = "12.5"

elbe_initvm_packagelist = ['python-elbe-buildenv',
                           'elbe-soap',
                           'python-elbe-common',
                           'elbe-daemon',
                           'elbe-schema',
                           'python-elbe-bin']

if pack_dir == '/usr/lib/python2.7/dist-packages/elbepack':
    is_devel = False
else:
    is_devel = True
