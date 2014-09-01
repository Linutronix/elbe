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

from elbepack.filesystem import ChRootFilesystem
from elbepack.shellhelper import CommandError, command_out
import os

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

    def execute(self, buildenv, target):
        # if self.command is not available invoke self.generate_command,
        # the result is then assigned to self.command.
        # otherwise allow subsitutions inside the command using format-function.
        if not hasattr(self, 'command'):
            if not hasattr(self, 'generate_command'):
                raise FinetuningError("No command is assigned to %s\nUse command atribute or generate_command function to define the command associated to this action" % type(self))
            else:
                self.command = self.generate_command(buildenv, target)
        else:
            self.command = self.command.format(node = self.node, buildenv=buildenv, target=target)

        # ensure self.input exists
        if not hasattr(self, 'input'):
            self.input = None

        # Execute command. If self.chroot is set command is executed inside a
        # chroot- environment
        if hasattr(self, 'chroot'):
            assert isinstance(self.chroot, ChRootFilesystem)
            self.command = "chroot {directory} {cmd}".format(directory=self.chroot.path, cmd=self.command)
            with self.chroot:
                self.returncode, self.output = command_out(self.command, input=self.input)
        else:
            self.returncode, self.output = command_out(self.command, input=self.input)
        self.success = True if self.returncode == 0 else False
        return self.success

    def write_log(self, log):
        cmd = self.command
        if not hasattr(self, 'input'):
            input = None
        else:
            input = self.input
        output = self.output
        ret = self.returncode
        log.command(cmd, input, output, ret)


class RmAction(FinetuningAction):

    tag = 'rm'

    def __init__(self, node):
        FinetuningAction.__init__(self, node)

    def generate_command(self, buildenv, target):
        return "rm -rvf {0}".format(target.fname(self.node.et.text))

FinetuningAction.register( RmAction )


class MkdirAction(FinetuningAction):

    tag = 'mkdir'

    def __init__(self, node):
        FinetuningAction.__init__(self, node)

    def generate_command(self, buildenv, target):
        return "mkdir -p {0}".format(target.fname(self.node.et.text))

FinetuningAction.register( MkdirAction )

class MknodAction(FinetuningAction):

    tag = 'mknod'

    def __init__(self, node):
        FinetuningAction.__init__(self, node)

    def generate_command(self, buildenv, target):
        return "mknod {0} {1}".format(target.fname(self.node.et.text), self.node.et.attrib['opts'])

FinetuningAction.register( MknodAction )

class BuildenvMkdirAction(FinetuningAction):

    tag = 'buildenv_mkdir'

    def __init__(self, node):
        FinetuningAction.__init__(self, node)

    def generate_command(self, buildenv, target):
        return "mkdir -p {0}".format(buildenv.fname(self.node.et.text))

FinetuningAction.register( BuildenvMkdirAction )


class CpAction(FinetuningAction):

    tag = 'cp'

    def __init__(self, node):
        FinetuningAction.__init__(self, node)

    def generate_command(self, buildenv, target):
        return "cp -av {0} {1}".format(target.fname(self.node.et.attrib['path']), target.fname(self.node.et.text))

FinetuningAction.register( CpAction )

class BuildenvCpAction(FinetuningAction):

    tag = 'buildenv_cp'

    def __init__(self, node):
        FinetuningAction.__init__(self, node)

    def generate_command(self, buildenv, target):
        return "cp -av {0} {1}".format(buildenv.fname(self.node.et.attrib['path']), buildenv.fname(self.node.et.text))

FinetuningAction.register( BuildenvCpAction )

class B2TCpAction(FinetuningAction):

    tag = 'b2t_cp'

    def __init__(self, node):
        FinetuningAction.__init__(self, node)

    def generate_command(self, buildenv, target):
        return "cp -av {0} {1}".format(buildenv.fname(self.node.et.attrib['path']), target.fname(self.node.et.text))

FinetuningAction.register( B2TCpAction )

class T2BCpAction(FinetuningAction):

    tag = 't2b_cp'

    def __init__(self, node):
        FinetuningAction.__init__(self, node)

    def generate_command(self, buildenv, target):
        return "cp -av {0} {1}".format(target.fname(self.node.et.attrib['path']), buildenv.fname(self.node.et.text))

FinetuningAction.register( T2BCpAction )

class MvAction(FinetuningAction):

    tag = 'mv'

    def __init__(self, node):
        FinetuningAction.__init__(self, node)

    def generate_command(self, buildenv, target):
        return "mv -v {0} {1}".format(target.fname(self.node.et.attrib['path']), target.fname(self.node.et.text))

FinetuningAction.register( MvAction )

class LnAction(FinetuningAction):

    tag = 'ln'

    def __init__(self, node):
        FinetuningAction.__init__(self, node)

    def generate_command(self, buildenv, target):
        self.chroot = target
        return "ln -s {0} {1}".format(self.node.et.attrib['path'], self.node.et.text)

FinetuningAction.register( LnAction )


class BuildenvMvAction(FinetuningAction):

    tag = 'buildenv_mv'

    def __init__(self, node):
        FinetuningAction.__init__(self, node)

    def generate_command(self, buildenv, target):
        return "mv -v {0} {1}".format(buildenv.fname(self.node.et.attrib['path']), buildenv.fname(self.node.et.text))

FinetuningAction.register( BuildenvMvAction )


class AddUserAction(FinetuningAction):

    tag = 'adduser'

    def __init__(self, node):
        FinetuningAction.__init__(self, node)

    def chroot(self, directory, cmd):
        return "chroot {directory} {cmd}".format(directory=directory, cmd=cmd)

    def execute(self, buildenv, target):
        self.commands = [{}, {}]

        username = self.node.et.text
        password = self.node.et.attrib['passwd']
        shell = self.node.et.attrib['shell']

        # Add user
        if 'groups' in self.node.et.attrib:
            groups = self.node.et.attrib['groups']
            cmd = "/usr/sbin/useradd -U -m -G {groups} -s {shell} {username}".format(shell=shell, username=username, groups=groups)
        else:
            cmd = "/usr/sbin/useradd -U -m -s {shell} {username}".format(shell=shell, username=username)
        self.commands[0]['cmd'] = self.chroot(target.path, cmd)

        # Set password
        cmd = 'passwd {0}'.format(username)
        self.commands[1]['cmd']   = self.chroot(target.path, cmd)
        self.commands[1]['input'] = password + '\n' + password

        # execute commands
        self.success = True
        with target:
            for command in self.commands:
                command['ret'], command['output'] = command_out(**command)
                if command['ret'] != 0:
                    self.success = False
                    break
        return self.success

    def write_log(self, log):
        for command in self.commands:
            log.command(**command)

FinetuningAction.register( AddUserAction )


class AddGroupAction(FinetuningAction):

    tag = 'addgroup'

    def __init__(self, node):
        FinetuningAction.__init__(self, node)

    def generate_command(self, buildenv, target):
        self.chroot = target
        return "/usr/sbin/groupadd -f {0}".format(self.node.et.text)

FinetuningAction.register( AddGroupAction )


class CmdAction(FinetuningAction):

    tag = 'command'

    def __init__(self, node):
        FinetuningAction.__init__(self, node)

    def generate_command(self, buildenv, target):
        self.input = self.node.et.text
        self.chroot = target
        return "/bin/sh"

FinetuningAction.register( CmdAction )

class BuildenvCmdAction(FinetuningAction):

    tag = 'buildenv_command'

    def __init__(self, node):
        FinetuningAction.__init__(self, node)

    def generate_command(self, buildenv, target):
        self.input = self.node.et.text
        self.chroot = buildenv
        return "/bin/sh"

FinetuningAction.register( BuildenvCmdAction )

class PurgeAction(FinetuningAction):

    tag = 'purge'

    def __init__(self, node):
        FinetuningAction.__init__(self, node)

    def generate_command(self, buildenv, target):
        self.chroot = buildenv
        return "dpkg --purge {0}".format(self.node.et.text)

FinetuningAction.register( PurgeAction )


def do_finetuning(xml, log, buildenv, target):

    if not xml.has('target/finetuning'):
        return

    for i in xml.node('target/finetuning'):
        try:
            action = FinetuningAction( i )
            action.execute(buildenv, target)
            action.write_log(log)
        except KeyError:
            print "Unimplemented finetuning action " + i.et.tag
        except CommandError:
            log.printo( "Finetuning Error, trying to continue anyways" )
