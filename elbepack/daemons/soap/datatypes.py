# ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (C) 2014  Linutronix GmbH
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


from spyne.model.complex import ComplexModel
from spyne.model.primitive import Unicode, DateTime

class SoapProject (ComplexModel):
    __namespace__ = 'soap'

    builddir = Unicode()
    name = Unicode()
    version = Unicode()
    status = Unicode()
    edit = DateTime()

    def __init__(self, prj):
        self.builddir = prj.builddir
        self.name = prj.name
        self.version = prj.version
        self.status = prj.status
        self.edit = prj.edit

class SoapFile (ComplexModel):
    __namespace__ = 'soap'

    name = Unicode()
    description = Unicode()

    def __init__(self, fi):
        self.name = fi.name
        self.description = fi.description

