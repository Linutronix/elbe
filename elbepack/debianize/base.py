#!/usr/bin/env python
#
# ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (C) 2016  Linutronix GmbH
#
# This file is part of ELBE.
#
# ELBE is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# ELBE is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with ELBE.  If not, see <http://www.gnu.org/licenses/>.

import os
import sys

from npyscreen import FormMultiPage
from npyscreen import TitleText, TitleSelectOne, ButtonPress

from shutil import copyfile

from mako.template import Template

def template (deb, fname):
    return Template(filename=fname).render(**deb)

class DebianizeBase (FormMultiPage):
    def __init__ (self):
        self.deb = { }
        self.tmpl_dir = None

        self.archs = ["armhf", "armel", "amd64", "i386", "powerpc"]
        self.formats = ["native", "git", "quilt"]
        self.releases = ["stable", "oldstable", "testing", "unstable", "experimental"]

        FormMultiPage.__init__ (self)

    def create (self):
        self.p_name = self.add_widget_intelligent (TitleText,
                name = "Name:", value = "elbe")

        self.p_version = self.add_widget_intelligent (TitleText,
                name = "Version:", value = "1.0")

        self.p_arch = self.add_widget_intelligent (TitleSelectOne,
                name = "Arch:",
                values = self.archs,
                value = [0],
                scroll_exit = True)

        self.source_format = self.add_widget_intelligent (TitleSelectOne,
                name="Format:",
                values = self.formats,
                value = [0],
                scroll_exit = True)

        self.release = self.add_widget_intelligent (TitleSelectOne,
                name = "Release:",
                values = self.releases,
                value = [0],
                scroll_exit = True)

        self.m_name = self.add_widget_intelligent (TitleText,
                name = "Maintainer:", value = "Max Mustermann")

        self.m_mail = self.add_widget_intelligent (TitleText,
                name = "Mail:", value = "max@mustermann.org")

        self.add_page ()
        self.gui ()

        self.add_widget_intelligent (ButtonPress, name = "Save",
                when_pressed_function=self.on_ok)

        self.add_widget_intelligent (ButtonPress, name = "Cancel",
                when_pressed_function=self.on_cancel)

    def on_ok (self):
        self.deb['p_name']       = self.p_name.get_value ()
        self.deb['p_version']    = self.p_version.get_value ()
        self.deb['p_arch']       = self.archs [self.p_arch.get_value ()[0]]
        self.deb['m_name']       = self.m_name.get_value ()
        self.deb['m_mail']       = self.m_mail.get_value ()
        self.deb['source_format']= self.formats [self.source_format.get_value ()[0]]
        self.deb['release']      = self.releases [self.release.get_value ()[0]]

        os.mkdir ('debian')
        os.mkdir ('debian/source')

        self.debianize ()

        with open ('debian/source/format', 'w') as f:
            mako = os.path.join(self.tmpl_dir, 'format.mako')
            f.write (template(self.deb, mako))

        copyfile (os.path.join(self.tmpl_dir, 'copyright'), 'debian/copyright')
        with open ('debian/compat', 'w') as f:
            f.write ('9')

        sys.exit (0)

    def on_cancel (self):
        sys.exit (-2)
