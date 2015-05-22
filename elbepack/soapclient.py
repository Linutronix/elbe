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

import binascii

class ClientAction(object):
    actiondict = {}
    @classmethod
    def register(cls, action):
        cls.actiondict[action.tag] = action
    @classmethod
    def print_actions(cls):
        print 'available subcommands are:'
        for a in cls.actiondict:
            print '   ' + a
    def __new__(cls, node):
        action = cls.actiondict[node]
        return object.__new__(action, node)
    def __init__(self, node):
        self.node = node

class ListProjectsAction(ClientAction):

    tag = 'list_projects'

    def __init__(self, node):
        ClientAction.__init__(self, node)

    def execute(self, client, user, passwd, args):
        projects = client.service.list_projects ()

        for p in projects.SoapProject:
            print p.builddir + '\t' + p.name + '\t' + p.version + '\t' + p.status + '\t' + str(p.edit)

ClientAction.register(ListProjectsAction)

class ListUsersAction(ClientAction):

    tag = 'list_users'

    def __init__(self, node):
        ClientAction.__init__(self, node)

    def execute(self, client, user, passwd, args):
        users = client.service.list_users (client)

        for u in users.string:
            print u

ClientAction.register(ListUsersAction)

class CreateProjectAction(ClientAction):

    tag = 'create_project'

    def __init__(self, node):
        ClientAction.__init__(self, node)

    def execute(self, client, user, passwd, args):
        if len (args) != 1:
            print "usage: elbe control create_project <xmlfile>"
            return

        filename = args[0]

        with file (filename, "r") as fp:
            print client.service.create_project (user, passwd,
                    binascii.b2a_base64(fp.read ()))

ClientAction.register(CreateProjectAction)

class ResetProjectAction(ClientAction):

    tag = 'reset_project'

    def __init__(self, node):
        ClientAction.__init__(self, node)

    def execute(self, client, user, passwd, args):
        if len (args) != 1:
            print "usage: elbe control reset_project <project_dir>"
            return

        builddir = args[0]
        print client.service.reset_project (user, passwd, builddir)

ClientAction.register(ResetProjectAction)


class DeleteProjectAction(ClientAction):

    tag = 'del_project'

    def __init__(self, node):
        ClientAction.__init__(self, node)

    def execute(self, client, user, passwd, args):
        if len (args) != 1:
            print "usage: elbe control del_project <project_dir>"
            return

        builddir = args[0]
        print client.service.reset_project (user, passwd, builddir)

ClientAction.register(DeleteProjectAction)

class SetXmlAction(ClientAction):

    tag = 'set_xml'

    def __init__(self, node):
        ClientAction.__init__(self, node)

    def execute(self, client, user, passwd, args):
        if len (args) != 2:
            print "usage: elbe control set_xml <project_dir> <xml>"
            return

        builddir = args[0]
        filename = args[1]
        with file (filename, "r") as fp:
            print client.service.set_xml (user, passwd, builddir,
                    binascii.b2a_base64(fp.read ()))

ClientAction.register(SetXmlAction)


class BuildAction(ClientAction):

    tag = 'build'

    def __init__(self, node):
        ClientAction.__init__(self, node)

    def execute(self, client, user, passwd, args):
        if len (args) != 1:
            print "usage: elbe control build <project_dir>"
            return

        builddir = args[0]
        print client.service.build (user, passwd, builddir)

ClientAction.register(BuildAction)


class GetFileAction(ClientAction):

    tag = 'get_file'

    def __init__(self, node):
        ClientAction.__init__(self, node)

    def execute(self, client, user, passwd, args):
        if len (args) != 2:
            print "usage: elbe control get_file <project_dir> <file>"
            return

        builddir = args[0]
        filename = args[1]

        fp = file (filename, "w")
        part = 0
        while True:
            ret = client.service.get_file (builddir, filename, part)
            if ret == "FileNotFound":
                print ret
                return
            if ret == "EndOfFile":
                fp.close ()
                print filename + " saved"
                return

            fp.write (binascii.a2b_base64 (ret))
            part = part + 1

        print filename + " unknown error"
        return

ClientAction.register(GetFileAction)


class GetFilesAction(ClientAction):

    tag = 'get_files'

    def __init__(self, node):
        ClientAction.__init__(self, node)

    def execute(self, client, user, passwd, args):
        if len (args) != 1:
            print "usage: elbe control get_files <project_dir>"
            return

        builddir = args[0]
        files = client.service.get_files (builddir)

        for f in files.SoapFile:
            if f.description:
                print "%s \t(%s)" % (f.name, f.description)
            else:
                print "%s" % (f.name)

ClientAction.register(GetFilesAction)
