# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2014, 2017 Linutronix GmbH

import argparse

from elbepack.cli import add_argument, add_arguments_from_decorated_function
from elbepack.db import ElbeDB


@add_argument('--name', default='root')
@add_argument('--fullname', default='Admin')
@add_argument('--password', default='foo')
@add_argument('--email', default='root@localhost')
def _init(args):
    ElbeDB.init_db(args.name, args.fullname, args.password, args.email)


def _list_projects(args):
    db = ElbeDB()
    projects = db.list_projects()

    for p in projects:
        print(f'{p.builddir}: {p.name} [{p.version}] {p.edit}')


@add_argument('project_dir')
def _create_project(args):
    db = ElbeDB()
    db.create_project(args.project_dir)


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


_actions = {
    'init':                _init,
    'list_projects':       _list_projects,
    'create_project':      _create_project,
    'del_project':         _del_project,
    'set_xml':             _set_xml,
    'build':               _build,
    'get_files':           _get_files,
    'reset_project':       _reset_project,
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
