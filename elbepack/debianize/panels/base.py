# ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (c) 2016-2017 Manuel Traut <manut@linutronix.de>
# Copyright (c) 2017 Torben Hohn <torben.hohn@linutronix.de>
# Copyright (c) 2017 Martin Kaistra <martin.kaistra@linutronix.de>
# Copyright (c) 2019 Olivier Dion <dion@linutronix.de>
#
# SPDX-License-Identifier: GPL-3.0-or-later


import os

from shutil import copyfile

from elbepack.debianize.base.tui import TUI
from elbepack.debianize.widgets.form import Form
from elbepack.debianize.widgets.edit import Edit
from elbepack.debianize.widgets.radio import RadioGroup

from elbepack.templates import template


class Arch(object):
    ARM64 = "arm64"
    ARMHF = "armhf"
    ARMEL = "armel"
    AMD64 = "amd64"
    I386  = "i386"
    POWER = "powerpc"


class Format(object):
    NATIVE = "native"
    GIT = "git"
    QUILT = "quilt"


class Release(object):
    STABLE = "stable"
    OLDSTABLE = "oldstable"
    TESTING = "testing"
    UNSTABLE = "unstable"
    EXPERIMENTAL = "experimental"


class Panel(Form):

    copyright_fname = "COPYING"

    def __init__(self, grid_elements):

        self.deb = {}
        self.tmpl_dir = None
        self.hint = None

        fullname = os.environ.get('DEBFULLNAME', "Max Mustermann")
        email = os.environ.get('DEBEMAIL', "max@mustermann.org")

        p_name = Edit("Name", "elbe")
        p_version = Edit("Version", "1.0")
        p_arch = RadioGroup("Arch", Arch, Arch.ARM64)
        src_fmt = RadioGroup("Format", Format, Format.NATIVE)
        release = RadioGroup("Release", Release, Release.STABLE)

        m_name = Edit("Maintainer", fullname)
        m_mail = Edit("Mail", email)

        grid = [
            {"p_name":p_name, "p_version":p_version},
            {"p_arch":p_arch,"release":release},
            {"source_format":src_fmt},
            {"m_name":m_name, "m_mail":m_mail},
        ]

        for element in grid_elements:
            grid.append(element)

        super(Panel, self).__init__(grid)


    def get_k_arch(self):
        """ get_k_arch() may be used in debianize() """

        if self.deb['p_arch'] == 'armhf':
            return 'arm'
        elif self.deb['p_arch'] == 'armel':
            return 'arm'
        elif self.deb['p_arch'] == 'amd64':
            return 'x86_64'
        else:
            return self.deb['p_arch']

    def on_submit(self, datas):

        for key, value in datas.items():
            self.deb[key] = str(value)

        self.deb['k_arch'] = self.get_k_arch()

        os.mkdir('debian')
        os.mkdir('debian/source')

        self.debianize()

        with open('debian/source/format', 'w') as f:
            mako = os.path.join(self.tmpl_dir, 'format.mako')
            f.write(template(mako, self.deb))

        copyfile(self.copyright_fname, 'debian/copyright')
        with open('debian/compat', 'w') as f:
            f.write('9')

        TUI.quit()
