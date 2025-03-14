# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2015-2017 Linutronix GmbH

import argparse
import subprocess

from elbepack.cli import add_argument, add_arguments_from_decorated_function
from elbepack.commands.preprocess import add_xmlpreprocess_passthrough_arguments
from elbepack.config import add_argument_sshport, add_arguments_soapclient
from elbepack.filesystem import TmpdirFilesystem
from elbepack.soapclient import ElbeSoapClient
from elbepack.xmlpreprocess import preprocess_file


@add_argument('--writeproject', help='write project name to file')
@add_argument('--ccache-size', dest='ccachesize', default='10G',
              help='set a limit for the compiler cache size '
                   '(should be a number followed by an optional '
                   'suffix: k, M, G, T. Use 0 for no limit.)')
@add_argument('--cross', dest='cross', default=False,
              action='store_true',
              help='Creates an environment for crossbuilding if '
                   'combined with create. Combined with build it'
                   ' will use this environment.')
@add_argument('--no-ccache', dest='noccache', default=False,
              action='store_true',
              help="Deactivates the compiler cache 'ccache'")
@add_argument('--xmlfile', help='xmlfile to use')
@add_argument('--project', help='project directory on the initvm')
@add_argument_sshport
def _create(control, args):
    if args.xmlfile:
        with preprocess_file(args.xmlfile, variants=args.variants, sshport=args.sshport,
                             soapport=args.soapport) as preproc:
            prjdir = control.service.new_project()

            control.set_xml(prjdir, preproc)

        if args.writeproject:
            wpf = open(args.writeproject, 'w')
            wpf.write(prjdir)
            wpf.close()

    elif args.project:
        prjdir = args.project
    else:
        args.parser.error('you need to specify --project option')

    print('Creating pbuilder')

    control.service.build_pbuilder(prjdir, args.cross, args.noccache, args.ccachesize)

    for msg in control.wait_busy(prjdir):
        print(msg)

    print('')
    print('Building Pbuilder finished !')
    print('')


@add_argument('--project', required=True, help='project directory on the initvm')
def _update(control, args):
    prjdir = args.project

    print('Updating pbuilder')

    control.service.update_pbuilder(prjdir)

    print('')
    print('Updating Pbuilder finished !')
    print('')


@add_argument('--origfile', default=[], action='append', help='upload orig file')
@add_argument('--profile', default='', help='profile that shall be built')
@add_argument('--skip-download', action='store_true', dest='skip_download', default=False,
              help='Skip downloading generated Files')
@add_argument('--source', dest='srcdir', default='.', help='directory containing sources')
@add_argument('--cross', dest='cross', default=False,
              action='store_true',
              help='Creates an environment for crossbuilding if '
                   'combined with create. Combined with build it'
                   ' will use this environment.')
@add_argument('--output', dest='outdir', default='..',
              help='directory where to save downloaded Files')
@add_argument('--xmlfile', help='xmlfile to use')
@add_argument('--project', help='project directory on the initvm')
def _build(control, args):
    tmp = TmpdirFilesystem()

    if args.xmlfile:
        prjdir = control.service.new_project()

        control.service.build_pbuilder(prjdir, args.cross, False, '10G')

        for msg in control.wait_busy(prjdir):
            print(msg)

        print('')
        print('Building Pbuilder finished !')
        print('')
    elif args.project:
        prjdir = args.project
        control.service.rm_log(prjdir)
    else:
        args.parser.error('you need to specify --project or --xmlfile option')

    print('')
    print('Packing Source into tmp archive')
    print('')

    subprocess.run(['tar', '-C', args.srcdir, '-czf', tmp.fname('pdebuild.tar.gz'), '.'],
                   check=True)

    for of in args.origfile:
        print('')
        print(f"Pushing orig file '{of}' into pbuilder")
        print('')
        control.set_orig(prjdir, of)

    print('')
    print('Pushing source into pbuilder')
    print('')

    control.set_pdebuild(prjdir, tmp.fname('pdebuild.tar.gz'), args.profile, args.cross)

    for msg in control.wait_busy(prjdir):
        print(msg)

    print('')
    print('Pdebuild finished !')
    print('')

    if args.skip_download:
        print('')
        print('Listing available files:')
        print('')

        for file in control.get_files(prjdir, None, pbuilder_only=True):
            print(f'{file.name}\t{file.description}')

        print('')
        print(f"Get Files with: 'elbe control get_file {prjdir} <filename>'")
    else:
        print('')
        print(f'Saving generated Files to {args.outdir}')
        print('')

        for file in control.get_files(prjdir, args.outdir, pbuilder_only=True):
            print(f'{file.name}\t{file.description}')


_actions = {
    'create': _create,
    'update': _update,
    'build':  _build,
}


def run_command(argv):
    aparser = argparse.ArgumentParser(prog='elbe pbuilder')

    add_xmlpreprocess_passthrough_arguments(aparser)
    add_arguments_soapclient(aparser)

    subparsers = aparser.add_subparsers(required=True)

    for action_name, do_action in _actions.items():
        action_parser = subparsers.add_parser(action_name)
        action_parser.set_defaults(func=do_action)
        add_arguments_from_decorated_function(action_parser, do_action)

    args = aparser.parse_args(argv)
    args.parser = aparser

    control = ElbeSoapClient.from_args(args)
    control.connect()

    args.func(control, args)
