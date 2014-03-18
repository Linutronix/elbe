# ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (C) 2013  Linutronix GmbH
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


class FinetuningAction(object):

    actiondict = {}

    @classmethod
    def register(cls, action):
        cls.actiondict[action.tag] = action

    def __new__(cls, node):
        action = cls.actiondict[node.tag]
        return object.__new__(action, node)

    def __init__(self, node):
        self.node = node


class RmAction(FinetuningAction):

    tag = 'rm'

    def __init__(self, node):
        FinetuningAction.__init__(self, node)

    def execute(self, log, buildenv, target):
        log.do( "rm -rvf " + target.fname( self.node.et.text ) )

FinetuningAction.register( RmAction )


class MkdirAction(FinetuningAction):

    tag = 'mkdir'

    def __init__(self, node):
        FinetuningAction.__init__(self, node)

    def execute(self, log, buildenv, target):
        log.do( "mkdir -p " + target.fname( self.node.et.text ) )

FinetuningAction.register( MkdirAction )


class CpAction(FinetuningAction):

    tag = 'cp'

    def __init__(self, node):
        FinetuningAction.__init__(self, node)

    def execute(self, log, buildenv, target):
        log.do( "cp -av " + target.fname( self.node.et.attrib['path'] ) + " " + target.fname( self.node.et.text ) )

FinetuningAction.register( CpAction )


class MvAction(FinetuningAction):

    tag = 'mv'

    def __init__(self, node):
        FinetuningAction.__init__(self, node)

    def execute(self, log, buildenv, target):
        log.do( "mv -v " + target.fname( self.node.et.attrib['path'] ) + " " + target.fname( self.node.et.text ) )

FinetuningAction.register( MvAction )


class CmdAction(FinetuningAction):

    tag = 'command'

    def __init__(self, node):
        FinetuningAction.__init__(self, node)

    def execute(self, log, buildenv, target):
        with target:
            target.enter_chroot ()
            log.do (self.node.et.text)
            target.leave_chroot ()

FinetuningAction.register( CmdAction )


def do_finetuning(xml, log, buildenv, target):

    if not xml.has('target/finetuning'):
        return

    for i in xml.node('target/finetuning'):
        try:
            action = FinetuningAction( i )
            action.execute(log, buildenv, target)
        except KeyError:
            print "Unimplemented finetuning action " + i.et.tag
