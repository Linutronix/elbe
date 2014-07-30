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

def list_users (client):
    return client.service.list_users ()

def list_projects (client):
    return client.service.list_projects ()

def get_files (client, builddir):
    return client.service.get_files (builddir)

def get_file (client, builddir, filename):
    fp = file (filename, "w")
    part = 0
    while True:
        ret = client.service.get_file (builddir, filename, part)
        if ret == "FileNotFound":
            return ret
        if ret == "EndOfFile":
            fp.close ()
            return filename + " saved"

        fp.write (binascii.a2b_base64 (ret))
        part = part + 1

    return filename + " unknown error"

def build_project (client, user, passwd, builddir):
    return client.service.build (user, passwd, builddir)

def set_xml (client, user, passwd, builddir, filename):
    print filename
    with file (filename, "r") as fp:
        return client.service.set_xml (user, passwd, builddir,
                binascii.b2a_base64(fp.read ()))

def del_project (client, user, passwd, builddir):
    return client.service.del_project (user, passwd, builddir)

def reset_project (client, user, passwd, builddir):
    return client.service.reset_project (user, passwd, builddir)

def create_project (client, user, passwd, filename):
    with file (filename, "r") as fp:
        return client.service.create_project (user, passwd,
                binascii.b2a_base64(fp.read ()))

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
        projects = list_projects (client)
        if not projects:
            return
        projects = projects.split(', ')
        for p in projects:
            print p.replace('____', '\t')

ClientAction.register(ListProjectsAction)

class ListUsersAction(ClientAction):

    tag = 'list_users'

    def __init__(self, node):
        ClientAction.__init__(self, node)

    def execute(self, client, user, passwd, args):
        users = list_users (client)
        if not users:
            return
        users = users.split(', ')
        for u in users:
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

        print create_project (client, user, passwd, args[0])

ClientAction.register(CreateProjectAction)

class ResetProjectAction(ClientAction):

    tag = 'reset_project'

    def __init__(self, node):
        ClientAction.__init__(self, node)

    def execute(self, client, user, passwd, args):
        if len (args) != 1:
            print "usage: elbe control reset_project <project_dir>"
            return

        print reset_project (client, user, passwd, args[0])

ClientAction.register(ResetProjectAction)


class DeleteProjectAction(ClientAction):

    tag = 'del_project'

    def __init__(self, node):
        ClientAction.__init__(self, node)

    def execute(self, client, user, passwd, args):
        if len (args) != 1:
            print "usage: elbe control del_project <project_dir>"
            return

        print del_project (client, user, passwd, args[0])

ClientAction.register(DeleteProjectAction)

class SetXmlAction(ClientAction):

    tag = 'set_xml'

    def __init__(self, node):
        ClientAction.__init__(self, node)

    def execute(self, client, user, passwd, args):
        if len (args) != 2:
            print "usage: elbe control set_xml <project_dir> <xml>"
            return

        print set_xml (client, user, passwd, args[0], args[1])

ClientAction.register(SetXmlAction)


class BuildAction(ClientAction):

    tag = 'build'

    def __init__(self, node):
        ClientAction.__init__(self, node)

    def execute(self, client, user, passwd, args):
        if len (args) != 1:
            print "usage: elbe control build <project_dir>"
            return

        print build_project (client, user, passwd, args[0])

ClientAction.register(BuildAction)


class GetFileAction(ClientAction):

    tag = 'get_file'

    def __init__(self, node):
        ClientAction.__init__(self, node)

    def execute(self, client, user, passwd, args):
        if len (args) != 2:
            print "usage: elbe control get_file <project_dir> <file>"
            return

        print get_file (client, args[0], args[1])

ClientAction.register(GetFileAction)


class GetFilesAction(ClientAction):

    tag = 'get_files'

    def __init__(self, node):
        ClientAction.__init__(self, node)

    def execute(self, client, user, passwd, args):
        if len (args) != 1:
            print "usage: elbe control get_files <project_dir>"
            return

        files = get_files (client, args[0])
        if not files:
            return
        files = files.split(", ")
        for f in files:
            print f

ClientAction.register(GetFilesAction)
