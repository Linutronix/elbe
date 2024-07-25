# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2014, 2017 Linutronix GmbH

import argparse
import sys
from getpass import getpass
from shutil import copyfileobj

from elbepack.cli import add_argument, add_arguments_from_decorated_function
from elbepack.db import ElbeDB, ElbeDBError


@add_argument('--name', default='root')
@add_argument('--fullname', default='Admin')
@add_argument('--password', default='foo')
@add_argument('--email', default='root@localhost')
@add_argument('--noadmin', dest='admin', default=True, action='store_false')
def _init(args):
    ElbeDB.init_db(args.name, args.fullname, args.password,
                   args.email, args.admin)


@add_argument('--fullname')
@add_argument('--password')
@add_argument('--email')
@add_argument('--admin', default=False, action='store_true')
@add_argument('username')
def _add_user(args):
    if not args.password:
        password = getpass('Password for the new user: ')
    else:
        password = args.password

    db = ElbeDB()
    db.add_user(args.username, args.fullname, password, args.email, args.admin)


@add_argument('--delete-projects', dest='delete_projects',
              default=False, action='store_true')
@add_argument('--quiet', dest='quiet',
              default=False, action='store_true')
@add_argument('userid', type=int)
def _del_user(args):
    db = ElbeDB()

    projects = db.del_user(args.userid)

    if projects:
        if not args.opt.quiet:
            if args.opt.delete_projects:
                print('removing projects owned by the deleted user:')
            else:
                print('keeping projects owned by the deleted user:')

    for p in projects:
        if not args.opt.quiet:
            print(f'{p.builddir}: {p.name} [{p.version}] {p.edit}')
        if args.opt.delete_projects:
            try:
                db.del_project(p.builddir)
            except ElbeDBError as e:
                print(f'  ==> {e} ')


def _list_projects(args):
    db = ElbeDB()
    projects = db.list_projects()

    for p in projects:
        print(f'{p.builddir}: {p.name} [{p.version}] {p.edit}')


def _list_users(args):
    db = ElbeDB()
    users = db.list_users()

    for u in users:
        print(f'{u.name}: {u.fullname} <{u.email}>')


@add_argument('--user', dest='user',
              help='user name of the designated project owner')
@add_argument('project_dir')
def _create_project(args):
    db = ElbeDB()
    owner_id = db.get_user_id(args.user)
    db.create_project(args.project_dir, owner_id)


@add_argument('project_dir')
def _del_project(args):
    db = ElbeDB()
    db.del_project(args.project_dir)


@add_argument('project_dir')
@add_argument('xml')
def _set_xml(args):
    db = ElbeDB()
    db.set_xml(args.project_dir, args.xml)


@add_argument('project_dir')
def _build(args):
    db = ElbeDB()
    db.set_busy(args.project_dir, ['empty_project', 'needs_build', 'has_changes',
                                   'build_done', 'build_failed'])
    try:
        ep = db.load_project(args.project_dir)
        ep.build()
        db.update_project_files(ep)
    except Exception as e:
        db.update_project_files(ep)
        db.reset_busy(args.project_dir, 'build_failed')
        print(str(e))
        return
    db.reset_busy(args.project_dir, 'build_done')


@add_argument('project_dir')
def _get_files(args):
    db = ElbeDB()
    files = db.get_project_files(args.project_dir)
    for f in files:
        if f.description:
            print(f'{f.name:40}  {f.description}')
        else:
            print(f.name)


@add_argument('--clean', dest='clean', default=False, action='store_true')
@add_argument('project_dir')
def _reset_project(args):
    db = ElbeDB()
    db.reset_project(args.project_dir, args.clean)


@add_argument('project_dir')
@add_argument('version')
def _set_project_version(args):
    db = ElbeDB()
    db.set_project_version(args.project_dir, args.version)


@add_argument('project_dir')
def _list_versions(args):
    db = ElbeDB()
    versions = db.list_project_versions(args.project_dir)

    for v in versions:
        if v.description:
            print(f'{v.version}: {v.description}')
        else:
            print(v.version)


@add_argument('--description', dest='description')
@add_argument('project_dir')
def _save_version(args):
    db = ElbeDB()
    db.save_version(args.project_dir, args.description)


@add_argument('project_dir')
@add_argument('version')
def _del_version(args):
    db = ElbeDB()
    db.del_version(args.project_dir, args.version)


@add_argument('project_dir')
@add_argument('version')
def _print_version_xml(args):
    db = ElbeDB()
    filename = db.get_version_xml(args.project_dir, args.version)
    with open(filename) as f:
        copyfileobj(f, sys.stdout)


_actions = {
    'init':                _init,
    'add_user':            _add_user,
    'del_user':            _del_user,
    'list_projects':       _list_projects,
    'list_users':          _list_users,
    'create_project':      _create_project,
    'del_project':         _del_project,
    'set_xml':             _set_xml,
    'build':               _build,
    'get_files':           _get_files,
    'reset_project':       _reset_project,
    'set_project_version': _set_project_version,
    'list_versions':       _list_versions,
    'save_version':        _save_version,
    'del_versions':        _del_version,
    'print_version_xml':   _print_version_xml,
}


def run_command(argv):
    aparser = argparse.ArgumentParser(prog='elbe db')
    subparsers = aparser.add_subparsers(required=True)

    for action_name, do_action in _actions.items():
        action_parser = subparsers.add_parser(action_name)
        action_parser.set_defaults(func=do_action)
        add_arguments_from_decorated_function(action_parser, do_action)

    args = aparser.parse_args(argv)

    args.func(args)
