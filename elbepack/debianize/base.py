# ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (c) 2016-2017 Manuel Traut <manut@linutronix.de>
# Copyright (c) 2017 Torben Hohn <torben.hohn@linutronix.de>
# Copyright (c) 2017 Martin Kaistra <martin.kaistra@linutronix.de>
#
# SPDX-License-Identifier: GPL-3.0-or-later

import os
import sys

from time import sleep
from shutil import copyfile

from npyscreen import FormMultiPage
from npyscreen import TitleText, TitleSelectOne, ButtonPress, notify

from elbepack.templates import template


class DebianizeBase (FormMultiPage):

    # pylint: disable=too-many-instance-attributes
    # pylint: disable=too-many-ancestors

    srctypes = {}

    @classmethod
    def register(cls, srctype):
        cls.srctypes[srctype.name] = srctype

    @classmethod
    def get_debianizer(cls):
        for t in cls.srctypes.values():
            match = True
            for f in t.files:
                if not os.path.exists(f):
                    match = False
            if match:
                return t

        raise KeyError

    def __init__(self):
        self.deb = {}
        self.tmpl_dir = None

        self.archs = ["arm64", "armhf", "armel", "amd64", "i386", "powerpc"]
        self.formats = ["native", "git", "quilt"]
        self.releases = [
            "stable",
            "oldstable",
            "testing",
            "unstable",
            "experimental"]

        self.hint = None

        FormMultiPage.__init__(self)

    def gui(self):
        raise NotImplementedError('gui() not implemented')

    def debianize(self):
        raise NotImplementedError('gui() not implemented')

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

    def create(self):
        self.p_name = self.add_widget_intelligent(TitleText,
                                                  name="Name:", value="elbe")

        self.p_version = self.add_widget_intelligent(
            TitleText, name="Version:", value="1.0")

        self.p_arch = self.add_widget_intelligent(TitleSelectOne,
                                                  name="Arch:",
                                                  values=self.archs,
                                                  value=[0],
                                                  scroll_exit=True)

        self.source_format = self.add_widget_intelligent(TitleSelectOne,
                                                         name="Format:",
                                                         values=self.formats,
                                                         value=[0],
                                                         scroll_exit=True)

        self.release = self.add_widget_intelligent(TitleSelectOne,
                                                   name="Release:",
                                                   values=self.releases,
                                                   value=[0],
                                                   scroll_exit=True)

        fullname = os.environ.get('DEBFULLNAME', failobj="Max Mustermann")
        self.m_name = self.add_widget_intelligent(
            TitleText, name="Maintainer:", value=fullname)

        email = os.environ.get('DEBEMAIL', failobj="max@mustermann.org")
        self.m_mail = self.add_widget_intelligent(TitleText,
                                                  name="Mail:", value=email)

        self.add_page()
        self.gui()

        self.add_widget_intelligent(ButtonPress, name="Save",
                                    when_pressed_function=self.on_ok)

        self.add_widget_intelligent(ButtonPress, name="Cancel",
                                    when_pressed_function=self.on_cancel)

    def on_ok(self):
        self.deb['p_name'] = self.p_name.get_value()
        self.deb['p_version'] = self.p_version.get_value()
        self.deb['p_arch'] = self.archs[self.p_arch.get_value()[0]]
        self.deb['m_name'] = self.m_name.get_value()
        self.deb['m_mail'] = self.m_mail.get_value()
        self.deb['source_format'] = self.formats[
                self.source_format.get_value()[0]]
        self.deb['release'] = self.releases[self.release.get_value()[0]]

        os.mkdir('debian')
        os.mkdir('debian/source')

        self.debianize()

        with open('debian/source/format', 'w') as f:
            mako = os.path.join(self.tmpl_dir, 'format.mako')
            f.write(template(mako, self.deb))

        copyfile('COPYING', 'debian/copyright')
        with open('debian/compat', 'w') as f:
            f.write('9')

        if self.hint:
            notify(self.hint, title='Hint')
            sleep(10)

        sys.exit(0)

    def on_cancel(self):
        sys.exit(-2)
