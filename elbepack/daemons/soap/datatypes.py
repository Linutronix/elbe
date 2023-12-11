# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2015-2017 Linutronix GmbH

from spyne.model.complex import ComplexModel
from spyne.model.primitive import Unicode, DateTime, Integer


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


class SoapCmdReply (ComplexModel):
    __namespace__ = 'soap'

    ret = Integer()
    out = Unicode()

    def __init__(self, ret, out):
        self.ret = ret
        self.out = out
