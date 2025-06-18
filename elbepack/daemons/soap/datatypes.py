# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2015-2017 Linutronix GmbH

from spyne.model.complex import ComplexModel
from spyne.model.primitive import Boolean, DateTime, Unicode, UnsignedInteger


class SoapProject (ComplexModel):
    __namespace__ = 'soap'

    builddir = Unicode()
    name = Unicode()
    version = Unicode()
    status = Unicode()
    edit = DateTime()


class SoapFile (ComplexModel):
    __namespace__ = 'soap'

    name = Unicode()
    description = Unicode()


class ServerStatus(ComplexModel):
    __namespace__ = 'soap'

    version = Unicode()
    is_devel = Boolean()
    storage_free_bytes = UnsignedInteger()
    memory_total_bytes = UnsignedInteger()
    memory_available_bytes = UnsignedInteger()
    orphan_project_directories = Unicode().customize(max_occurs='unbounded')
