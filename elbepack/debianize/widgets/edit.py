# ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (c) 2019 Olivier Dion <dion@linutronix.de>
#
# SPDX-License-Identifier: GPL-3.0-or-later


import urwid


def Edit(header='', default='', linebox=True, multiline=False):
    this = urwid.Edit(("header", "{}\n".format(header)), default, multiline=multiline)
    if linebox:
        this = urwid.LineBox(this)
    return this
