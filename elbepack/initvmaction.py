#!/usr/bin/env python
#
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

from __future__ import print_function

from elbepack.directories import examples_dir, elbe_exe
from elbepack.shellhelper import CommandError, system, system_out
import sys

import os


class InitVMError(Exception):
    def __init__(self, str):
        Exception.__init__(self, str)

class InitVMAction(object):
    actiondict = {}
    @classmethod
    def register(cls, action):
        cls.actiondict[action.tag] = action
    @classmethod
    def print_actions(cls):
        print ('available subcommands are:', file=sys.stderr)
        for a in cls.actiondict:
            print ('   ' + a, file=sys.stderr)
    def __new__(cls, node):
        action = cls.actiondict[node]
        return object.__new__(action, node)
    def __init__(self, node):
        self.node = node

class StartAction(InitVMAction):

    tag = 'start'

    def __init__(self, node):
        InitVMAction.__init__(self, node)

    def execute(self, initvmdir, args):
        have_session = os.system( "tmux has-session -t ElbeInitVMSession >/dev/null 2>&1" )
        if have_session == 256:
            system( 'TMUX= tmux new-session -d -c "%s" -s ElbeInitVMSession -n initvm "make run-con"' % initvmdir )
        else:
            print ("ElbeInitVMSession already exists in tmux.", file=sys.stderr)
            print ("Try 'elbe initvm attach' to attach to the session.", file=sys.stderr) 
            sys.exit(20)

InitVMAction.register(StartAction)

class EnsureAction(InitVMAction):

    tag = 'ensure'

    def __init__(self, node):
        InitVMAction.__init__(self, node)

    def execute(self, initvmdir, args):
        have_session = os.system( "tmux has-session -t ElbeInitVMSession >/dev/null 2>&1" )
        if have_session == 256:
            system( 'TMUX= tmux new-session -d -c "%s" -s ElbeInitVMSession -n initvm "make run-con"' % initvmdir )

InitVMAction.register(EnsureAction)

class AttachAction(InitVMAction):

    tag = 'attach'

    def __init__(self, node):
        InitVMAction.__init__(self, node)

    def execute(self, initvmdir, args):
        have_session = os.system( "tmux has-session -t ElbeInitVMSession >/dev/null 2>&1" )
        if have_session == 0:
            if os.environ.has_key('TMUX'):
                system( 'tmux link-window -s ElbeInitVMSession:initvm' )
            else:
                system( 'tmux attach -t ElbeInitVMSession' )
        else:
            print ("ElbeInitVMSession does not exist in tmux.", file=sys.stderr)
            print ("Try 'elbe initvm start' to start the session.", file=sys.stderr) 
            sys.exit(20)

InitVMAction.register(AttachAction)

class StartBuildAction(InitVMAction):

    tag = 'start_build'

    def __init__(self, node):
        InitVMAction.__init__(self, node)

    def execute(self, initvmdir, args):
        have_session = os.system( "tmux has-session -t ElbeInitVMSession >/dev/null 2>&1" )
        if have_session == 256:
            system( 'TMUX= tmux new-session -d -c "%s" -s ElbeInitVMSession -n initvm "make"' % initvmdir )
        else:
            print ("ElbeInitVMSession already exists in tmux.", file=sys.stderr)
            print ("Try 'elbe initvm attach' to attach to the session.", file=sys.stderr) 
            sys.exit(20)

InitVMAction.register(StartBuildAction)



