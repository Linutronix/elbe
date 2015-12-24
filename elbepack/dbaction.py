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

import os
import sys

from optparse import OptionParser
from getpass import getpass
from shutil import copyfileobj
from elbepack.db import ElbeDB, ElbeDBError

class DbAction(object):

    actiondict = {}

    @classmethod
    def register(cls, action):
        cls.actiondict[action.tag] = action

    @classmethod
    def print_actions(cls):
        print 'available actions are:'
        for a in cls.actiondict:
            print '   ' + a

    def __new__(cls, node):
        action = cls.actiondict[node]
        return object.__new__(action, node)

    def __init__(self, node):
        self.node = node

class InitAction(DbAction):
    tag = 'init'

    def __init__(self, node):
        DbAction.__init__(self, node)

    def execute(self, args):
        oparser = OptionParser (usage="usage: %prog db init [options]")
        oparser.add_option ("--name", dest="name", default="root")
        oparser.add_option ("--fullname", dest="fullname", default="Admin")
        oparser.add_option ("--password", dest="password", default="foo")
        oparser.add_option ("--email", dest="email", default="root@localhost")
        oparser.add_option ("--noadmin", dest="admin", default=True,
                action="store_false")

        (opt, arg) = oparser.parse_args (args)

        ElbeDB.init_db (opt.name, opt.fullname, opt.password,
                        opt.email, opt.admin)

DbAction.register(InitAction)

class AddUserAction(DbAction):
    tag = 'add_user'

    def __init__(self, node):
        DbAction.__init__(self, node)

    def execute(self, args):
        oparser = OptionParser (usage="usage: %prog db add_user [options] username")
        oparser.add_option ("--fullname", dest="fullname")
        oparser.add_option ("--password", dest="password")
        oparser.add_option ("--email", dest="email")
        oparser.add_option ("--admin", dest="admin", default=False,
                action="store_true")

        (opt, arg) = oparser.parse_args (args)

        if len(arg) != 1:
            print "wrong number of arguments"
            oparser.print_help()
            return

        if not opt.password:
            password = getpass('Password for the new user: ')
        else:
            password = opt.password

        db = ElbeDB()
        db.add_user( arg[0], opt.fullname, password, opt.email, opt.admin )

DbAction.register(AddUserAction)

class DelUserAction(DbAction):
    tag = 'del_user'

    def __init__(self, node):
        DbAction.__init__(self, node)

    def execute(self, args):
        oparser = OptionParser (usage="usage: %prog db del_user [options] <userid>")
        oparser.add_option ("--delete-projects", dest="delete_projects",
                default=False, action="store_true")
        oparser.add_option ("--quiet", dest="quiet",
                default=False, action="store_true")

        (opt, arg) = oparser.parse_args (args)

        if len(arg) != 1:
            print "usage: elbe db del_user <userid>"
            return

        try:
            userid = int(arg[0])
        except:
            print "userid must be an integer"
            return

        db = ElbeDB()

        projects = db.del_user( userid )

        if projects:
            if not opt.quiet:
                if opt.delete_projects:
                    print "removing projects owned by the deleted user:"
                else:
                    print "keeping projects owned by the deleted user:"

        for p in projects:
            if not opt.quiet:
                print p.builddir + ":", p.name, "[", p.version, "]", p.edit
            if opt.delete_projects:
                try:
                    db.del_project( p.builddir )
                except ElbeDBError as e:
                    print "  ==> ", e

DbAction.register(DelUserAction)

class ListProjectsAction(DbAction):

    tag = 'list_projects'

    def __init__(self, node):
        DbAction.__init__(self, node)

    def execute(self, args):
        db = ElbeDB()
        projects = db.list_projects ()

        for p in projects:
            print p.builddir+":", p.name, "[", p.version, "]", p.edit

DbAction.register(ListProjectsAction)

class ListUsersAction(DbAction):

    tag = 'list_users'

    def __init__(self, node):
        DbAction.__init__(self, node)

    def execute(self, args):
        db = ElbeDB()
        users = db.list_users ()

        for u in users:
            print u.name+":", u.fullname, "<"+u.email+">"

DbAction.register(ListUsersAction)

class CreateProjectAction(DbAction):

    tag = 'create_project'

    def __init__(self, node):
        DbAction.__init__(self, node)

    def execute(self, args):
        oparser = OptionParser (
                usage="usage: %prog db create_project [options] <project_dir>" )
        oparser.add_option( "--user", dest="user",
                help="user name of the designated project owner" )
        (opt, arg) = oparser.parse_args(args)

        if len (arg) != 1:
            oparser.print_help()
            return

        db = ElbeDB()
        owner_id = db.get_user_id( opt.user )
        db.create_project (arg[0], owner_id)

DbAction.register(CreateProjectAction)

class DeleteProjectAction(DbAction):

    tag = 'del_project'

    def __init__(self, node):
        DbAction.__init__(self, node)

    def execute(self, args):
        if len (args) != 1:
            print "usage: elbe db del_project <project_dir>"
            return

        db = ElbeDB()
        db.del_project (args[0])

DbAction.register(DeleteProjectAction)

class SetXmlAction(DbAction):

    tag = 'set_xml'

    def __init__(self, node):
        DbAction.__init__(self, node)

    def execute(self, args):
        if len (args) != 2:
            print "usage: elbe db set_xml <project_dir> <xml>"
            return

        db = ElbeDB()
        db.set_xml (args[0], args[1])

DbAction.register(SetXmlAction)


class BuildAction(DbAction):

    tag = 'build'

    def __init__(self, node):
        DbAction.__init__(self, node)

    def execute(self, args):
        if len (args) != 1:
            print "usage: elbe db build <project_dir>"
            return

        db = ElbeDB()
        db.set_busy( args[0], [ "empty_project", "needs_build", "has_changes",
                                "build_done", "build_failed" ] )
        try:
            ep = db.load_project( args[0] )
            ep.build( skip_debootstrap = True )
            db.update_project_files( ep )
        except Exception as e:
            db.update_project_files( ep )
            db.reset_busy( args[0], "build_failed" )
            print e
            return
        db.reset_busy( args[0], "build_done" )

DbAction.register(BuildAction)


class GetFilesAction(DbAction):

    tag = 'get_files'

    def __init__(self, node):
        DbAction.__init__(self, node)

    def execute(self, args):
        if len (args) != 1:
            print "usage: elbe db get_files <project_dir>"
            return

        db = ElbeDB()
        files = db.get_project_files (args[0])
        for f in files:
            if f.description:
                print "%-40s  %s" % (f.name, f.description)
            else:
                print f.name

DbAction.register(GetFilesAction)


class ResetProjectAction(DbAction):

    tag = 'reset_project'

    def __init__(self, node):
        DbAction.__init__(self, node)

    def execute(self, args):
        oparser = OptionParser (
                usage="usage: %prog db reset_project [options] <project_dir>")
        oparser.add_option ("--clean", dest="clean", default=False,
                action="store_true")

        (opt, arg) = oparser.parse_args (args)

        if len(arg) != 1:
            print "wrong number of arguments"
            oparser.print_help()
            return

        db = ElbeDB()
        db.reset_project (arg[0], opt.clean)

DbAction.register(ResetProjectAction)


class SetProjectVersionAction(DbAction):

    tag = 'set_project_version'

    def __init__(self, node):
        DbAction.__init__(self, node)

    def execute(self, args):
        if len(args) != 2:
            print "usage: elbe db set_project_version <project_dir> <version>"
            return

        db = ElbeDB()
        db.set_project_version( args[0], args[1] )

DbAction.register(SetProjectVersionAction)


class ListVersionsAction(DbAction):

    tag = 'list_versions'

    def __init__(self, node):
        DbAction.__init__(self, node)

    def execute(self, args):
        if len(args) != 1:
            print "usage: elbe db list_versions <project_dir>"
            return

        db = ElbeDB()
        versions = db.list_project_versions (args[0])

        for v in versions:
            if v.description:
                print v.version + ": " + v.description
            else:
                print v.version

DbAction.register(ListVersionsAction)


class SaveVersionAction(DbAction):

    tag = 'save_version'

    def __init__(self, node):
        DbAction.__init__(self, node)

    def execute(self, args):
        oparser = OptionParser (usage="usage: %prog db save_version <project_dir>")
        oparser.add_option ("--description", dest="description")

        (opt, arg) = oparser.parse_args (args)

        if len(arg) != 1:
            print "wrong number of arguments"
            oparser.print_help()
            return

        db = ElbeDB()
        db.save_version( arg[0], opt.description )

DbAction.register(SaveVersionAction)


class DelVersionAction(DbAction):

    tag = 'del_version'

    def __init__(self, node):
        DbAction.__init__(self, node)

    def execute(self, args):
        if len(args) != 2:
            print "usage: elbe db del_version <project_dir> <version>"
            return

        db = ElbeDB()
        db.del_version( args[0], args[1] )

DbAction.register(DelVersionAction)


class PrintVersionXMLAction(DbAction):

    tag = 'print_version_xml'

    def __init__(self, node):
        DbAction.__init__(self, node)

    def execute(self, args):
        if len(args) != 2:
            print "usage: elbe db print_version_xml <project_dir> <version>"
            return

        db = ElbeDB()
        filename = db.get_version_xml( args[0], args[1] )
        with open( filename ) as f:
            copyfileobj( f, sys.stdout )

DbAction.register(PrintVersionXMLAction)
