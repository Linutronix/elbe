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
from elbepack.filesystem  import wdfs

import sys

import os
import datetime


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

    def execute(self, initvmdir, opt, args):
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

    def execute(self, initvmdir, opt, args):
        have_session = os.system( "tmux has-session -t ElbeInitVMSession >/dev/null 2>&1" )
        if have_session == 256:
            system( 'TMUX= tmux new-session -d -c "%s" -s ElbeInitVMSession -n initvm "make run-con"' % initvmdir )

InitVMAction.register(EnsureAction)

class AttachAction(InitVMAction):

    tag = 'attach'

    def __init__(self, node):
        InitVMAction.__init__(self, node)

    def execute(self, initvmdir, opt, args):
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

    def execute(self, initvmdir, opt, args):
        have_session = os.system( "tmux has-session -t ElbeInitVMSession >/dev/null 2>&1" )
        if have_session == 256:
            system( 'TMUX= tmux new-session -d -c "%s" -s ElbeInitVMSession -n initvm "make"' % initvmdir )
        else:
            print ("ElbeInitVMSession already exists in tmux.", file=sys.stderr)
            print ("Try 'elbe initvm attach' to attach to the session.", file=sys.stderr)
            sys.exit(20)

InitVMAction.register(StartBuildAction)

class CreateAction(InitVMAction):

    tag = 'create'

    def __init__(self, node):
        InitVMAction.__init__(self, node)

    def execute(self, initvmdir, opt, args):
        have_session = os.system( "tmux has-session -t ElbeInitVMSession >/dev/null 2>&1" )
        if have_session == 0:
            print ("ElbeInitVMSession already exists in tmux.", file=sys.stderr)
            print ("", file=sys.stderr)
            print ("There can only exist a single ElbeInitVMSession, and this session", file=sys.stderr)
            print ("can also be used to make your build.", file=sys.stderr)
            print ("See 'elbe initvm attach' and 'elbe control'", file=sys.stderr)
            sys.exit(20)

        if len(args) == 1:
            # We have an xml file, use that for elbe init
            exampl = args[0]
        else:
            # No xml File was specified, build the default elbe-init-with-ssh
            exampl = os.path.join (examples_dir, "elbe-init-with-ssh.xml")

        try:
            if opt.devel:
                devel = ' --devel'
            else:
                devel = ''

            if opt.cdrom:
                system ('%s init %s --directory "%s" --cdrom "%s" "%s"' % (elbe_exe, devel, initvmdir, opt.cdrom, exampl))
            else:
                system ('%s init %s --directory "%s" "%s"' % (elbe_exe, devel, initvmdir, exampl))

        except CommandError:
            print ("'elbe init' Failed", file=sys.stderr)
            print ("Giving up", file=sys.stderr)
            sys.exit(20)

        try:
            system ('cd "%s"; make' % (initvmdir))
        except CommandError:
            print ("Building the initvm Failed", file=sys.stderr)
            print ("Giving up", file=sys.stderr)
            sys.exit(20)

        try:
            system ('%s initvm start --directory "%s"' % (elbe_exe, initvmdir))
        except CommandError:
            print ("Starting the initvm Failed", file=sys.stderr)
            print ("Giving up", file=sys.stderr)
            sys.exit(20)

        if len(args) == 1:
            try:
                prjdir = system_out ('%s control create_project "%s"' % (elbe_exe, args[0]))
            except CommandError:
                print ("elbe control Failed", file=sys.stderr)
                print ("Giving up", file=sys.stderr)
                sys.exit(20)

            prjdir = prjdir.strip()

            if opt.cdrom is not None:
                print ("Uploading CDROM. This might take a while")
                try:
                    system ('%s control set_cdrom "%s" "%s"' % (elbe_exe, prjdir, opt.cdrom) )
                except CommandError:
                    print ("elbe control Failed", file=sys.stderr)
                    print ("Giving up", file=sys.stderr)
                    sys.exit(20)

                print ("Upload finished")

            try:
                system ('%s control build "%s"' % (elbe_exe, prjdir) )
            except CommandError:
                print ("elbe control Failed", file=sys.stderr)
                print ("Giving up", file=sys.stderr)
                sys.exit(20)

            try:
                system ('%s control wait_busy "%s"' % (elbe_exe, prjdir) )
            except CommandError:
                print ("elbe control Failed", file=sys.stderr)
                print ("Giving up", file=sys.stderr)
                sys.exit(20)

            print ("")
            print ("Build finished !")
            print ("")
            try:
                system ('%s control dump_file "%s" validation.txt' % (elbe_exe, prjdir) )
            except CommandError:
                print ("elbe control Failed", file=sys.stderr)
                print ("Giving up", file=sys.stderr)
                sys.exit(20)

            if opt.skip_download:
                print ("")
                print ("Listing vailable files:")
                print ("")
                try:
                    system ('%s control get_files "%s"' % (elbe_exe, prjdir) )
                except CommandError:
                    print ("elbe control Failed", file=sys.stderr)
                    print ("Giving up", file=sys.stderr)
                    sys.exit(20)

                print ("")
                print ('Get Files with: elbe control get_file "%s" <filename>' % prjdir)
            else:
                print ("")
                print ("Getting generated Files")
                print ("")

                # Create download directory with timestamp,
                # if necessary
                if opt.outdir is None:
                    builddir_name = "elbe-build-" + datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
                    wdfs.mkdir_p (builddir_name)
                    opt.outdir = wdfs.fname (builddir_name)

                    print ("Saving generated Files to %s" % opt.outdir)

                try:
                    system ('%s control get_files --output "%s" "%s"' % (elbe_exe, opt.outdir, prjdir) )
                except CommandError:
                    print ("elbe control Failed", file=sys.stderr)
                    print ("Giving up", file=sys.stderr)
                    sys.exit(20)

InitVMAction.register(CreateAction)

class SubmitAction(InitVMAction):

    tag = 'submit'

    def __init__(self, node):
        InitVMAction.__init__(self, node)

    def execute(self, initvmdir, opt, args):
        have_session = os.system( "tmux has-session -t ElbeInitVMSession >/dev/null 2>&1" )
        if have_session == 256:
            print ("ElbeInitVMSession does not exist in tmux.", file=sys.stderr)
            print ("Try 'elbe initvm start' to start the session.", file=sys.stderr)
            sys.exit(20)

        try:
            system ('%s initvm ensure --directory "%s"' % (elbe_exe, initvmdir))
        except CommandError:
            print ("Starting the initvm Failed", file=sys.stderr)
            print ("Giving up", file=sys.stderr)
            sys.exit(20)

        if len(args) == 1:
            try:
                prjdir = system_out ('%s control create_project --retries 60 "%s"' % (elbe_exe, args[0]))
            except CommandError:
                print ("elbe control Failed", file=sys.stderr)
                print ("Giving up", file=sys.stderr)
                sys.exit(20)

            prjdir = prjdir.strip()

            if opt.cdrom is not None:
                print ("Uploading CDROM. This might take a while")
                try:
                    system ('%s control set_cdrom "%s" "%s"' % (elbe_exe, prjdir, opt.cdrom) )
                except CommandError:
                    print ("elbe control Failed", file=sys.stderr)
                    print ("Giving up", file=sys.stderr)
                    sys.exit(20)

                print ("Upload finished")

            try:
                system ('%s control build "%s"' % (elbe_exe, prjdir) )
            except CommandError:
                print ("elbe control Failed", file=sys.stderr)
                print ("Giving up", file=sys.stderr)
                sys.exit(20)

            print ("Build started, waiting till it finishes")

            try:
                system ('%s control wait_busy "%s"' % (elbe_exe, prjdir) )
            except CommandError:
                print ("elbe control Failed", file=sys.stderr)
                print ("Giving up", file=sys.stderr)
                sys.exit(20)

            print ("")
            print ("Build finished !")
            print ("")
            try:
                system ('%s control dump_file "%s" validation.txt' % (elbe_exe, prjdir) )
            except CommandError:
                print ("elbe control Failed", file=sys.stderr)
                print ("Giving up", file=sys.stderr)
                sys.exit(20)

            if opt.skip_download:
                print ("")
                print ("Listing vailable files:")
                print ("")
                try:
                    system ('%s control get_files "%s"' % (elbe_exe, prjdir) )
                except CommandError:
                    print ("elbe control Failed", file=sys.stderr)
                    print ("Giving up", file=sys.stderr)
                    sys.exit(20)

                print ("")
                print ('Get Files with: elbe control get_file "%s" <filename>' % prjdir)
            else:
                print ("")
                print ("Getting generated Files")
                print ("")

                # Create download directory with timestamp,
                # if necessary
                if opt.outdir is None:
                    builddir_name = "elbe-build-" + datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
                    wdfs.mkdir_p (builddir_name)
                    opt.outdir = wdfs.fname (builddir_name)

                    print ("Saving generated Files to %s" % opt.outdir)

                try:
                    system ('%s control get_files --output "%s" "%s"' % (elbe_exe, opt.outdir, prjdir) )
                except CommandError:
                    print ("elbe control Failed", file=sys.stderr)
                    print ("Giving up", file=sys.stderr)
                    sys.exit(20)

InitVMAction.register(SubmitAction)

