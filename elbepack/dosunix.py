# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2015-2022 Linutronix GmbH

def dos2unix_str(d):
    return d.replace('\r\n', '\n')


def unix2dos_str(d):
    d = d.replace('\n', '\r\n')
    d = d.replace('\r\r\n', '\r\n')
    return d


def __rewrite(fn, rw_func):
    with open(fn, 'r+') as f:
        d = rw_func(f.read())
        f.seek(0)
        f.write(d)
        f.truncate()


def dos2unix(fn):
    __rewrite(fn, dos2unix_str)


def unix2dos(fn):
    __rewrite(fn, unix2dos_str)
