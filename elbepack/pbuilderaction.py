# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2015-2017 Linutronix GmbH

import os
import subprocess
import sys

from elbepack.directories import run_elbe
from elbepack.filesystem import TmpdirFilesystem
from elbepack.xmlpreprocess import preprocess_file


def cmd_exists(x):
    return any(os.access(os.path.join(path, x), os.X_OK)
               for path in os.environ['PATH'].split(os.pathsep))

# Create download directory with timestamp,
# if necessary


def ensure_outdir(opt):
    if opt.outdir is None:
        opt.outdir = '..'

    print(f'Saving generated Files to {opt.outdir}')


class PBuilderError(Exception):
    pass


class PBuilderAction:
    actiondict = {}

    @classmethod
    def register(cls, action):
        cls.actiondict[action.tag] = action

    @classmethod
    def print_actions(cls):
        print('available subcommands are:', file=sys.stderr)
        for a in cls.actiondict:
            print(f'   {a}', file=sys.stderr)

    def __new__(cls, node):
        action = cls.actiondict[node]
        return object.__new__(action)

    def __init__(self, node):
        self.node = node

    def execute(self, _opt, _args):
        raise NotImplementedError('execute() not implemented')


class CreateAction(PBuilderAction):

    tag = 'create'

    def execute(self, opt, _args):
        crossopt = []
        if opt.cross:
            crossopt = ['--cross']
        if opt.noccache:
            ccacheopt = ['--no-ccache']
        else:
            ccacheopt = ['--ccache-size', opt.ccachesize]

        if opt.xmlfile:
            with preprocess_file(opt.xmlfile, opt.variants) as preproc:
                ps = run_elbe(['control', 'create_project'],
                              capture_output=True, encoding='utf-8')
                if ps.returncode != 0:
                    print('elbe control create_project failed.',
                          file=sys.stderr)
                    print(ps.stderr, file=sys.stderr)
                    print('Giving up', file=sys.stderr)
                    sys.exit(152)

                prjdir = ps.stdout.strip()
                ps = run_elbe(['control', 'set_xml', prjdir, preproc],
                              capture_output=True, encoding='utf-8')

                if ps.returncode != 0:
                    print('elbe control set_xml failed.', file=sys.stderr)
                    print(ps.stderr, file=sys.stderr)
                    print('Giving up', file=sys.stderr)
                    sys.exit(153)

            if opt.writeproject:
                wpf = open(opt.writeproject, 'w')
                wpf.write(prjdir)
                wpf.close()

        elif opt.project:
            prjdir = opt.project
        else:
            print('you need to specify --project option', file=sys.stderr)
            sys.exit(155)

        print('Creating pbuilder')

        try:
            run_elbe(['control', 'build_pbuilder', prjdir, *crossopt, *ccacheopt],
                     check=True)
        except subprocess.CalledProcessError:
            print('elbe control build_pbuilder Failed', file=sys.stderr)
            print('Giving up', file=sys.stderr)
            sys.exit(156)

        try:
            run_elbe(['control', 'wait_busy', prjdir], check=True)
        except subprocess.CalledProcessError:
            print('elbe control wait_busy Failed', file=sys.stderr)
            print('Giving up', file=sys.stderr)
            sys.exit(157)

        print('')
        print('Building Pbuilder finished !')
        print('')


PBuilderAction.register(CreateAction)


class UpdateAction(PBuilderAction):

    tag = 'update'

    def execute(self, opt, _args):

        if not opt.project:
            print('you need to specify --project option', file=sys.stderr)
            sys.exit(158)

        prjdir = opt.project

        print('Updating pbuilder')

        try:
            run_elbe(['control', 'update_pbuilder', prjdir], check=True)
        except subprocess.CalledProcessError:
            print('elbe control update_pbuilder Failed', file=sys.stderr)
            print('Giving up', file=sys.stderr)
            sys.exit(159)

        print('')
        print('Updating Pbuilder finished !')
        print('')


PBuilderAction.register(CreateAction)


class BuildAction(PBuilderAction):

    tag = 'build'

    def execute(self, opt, _args):

        crossopt = []
        if opt.cross:
            crossopt = ['--cross']
        tmp = TmpdirFilesystem()

        if opt.xmlfile:
            ps = run_elbe(['control', 'create_project', '--retries', '60', opt.xmlfile],
                          capture_output=True, encoding='utf-8')
            if ps.returncode != 0:
                print('elbe control create_project failed.', file=sys.stderr)
                print(ps.stderr, file=sys.stderr)
                print('Giving up', file=sys.stderr)
                sys.exit(160)

            prjdir = ps.stdout.strip()

            try:
                run_elbe(['control', 'build_pbuilder', prjdir], check=True)
            except subprocess.CalledProcessError:
                print('elbe control build_pbuilder Failed', file=sys.stderr)
                print('Giving up', file=sys.stderr)
                sys.exit(161)

            try:
                run_elbe(['control', 'wait_busy', prjdir], check=True)
            except subprocess.CalledProcessError:
                print('elbe control wait_busy Failed', file=sys.stderr)
                print('Giving up', file=sys.stderr)
                sys.exit(162)

            print('')
            print('Building Pbuilder finished !')
            print('')
        elif opt.project:
            prjdir = opt.project
            run_elbe(['control', 'rm_log', prjdir], check=True)
        else:
            print(
                'you need to specify --project or --xmlfile option',
                file=sys.stderr)
            sys.exit(163)

        print('')
        print('Packing Source into tmp archive')
        print('')
        try:
            subprocess.run(['tar', '-C', opt.srcdir, '-czf', tmp.fname('pdebuild.tar.gz'), '.'],
                           check=True)
        except subprocess.CalledProcessError:
            print('tar Failed', file=sys.stderr)
            print('Giving up', file=sys.stderr)
            sys.exit(164)

        for of in opt.origfile:
            print('')
            print(f"Pushing orig file '{of}' into pbuilder")
            print('')
            try:
                run_elbe(['control', 'set_orig', prjdir, of], check=True)
            except subprocess.CalledProcessError:
                print('elbe control set_orig Failed', file=sys.stderr)
                print('Giving up', file=sys.stderr)
                sys.exit(165)

        print('')
        print('Pushing source into pbuilder')
        print('')

        try:
            run_elbe([
                'control', 'set_pdebuild', '--cpuset', str(opt.cpuset),
                '--profile', opt.profile, *crossopt,
                prjdir, tmp.fname('pdebuild.tar.gz'),
            ], check=True)
        except subprocess.CalledProcessError:
            print('elbe control set_pdebuild Failed', file=sys.stderr)
            print('Giving up', file=sys.stderr)
            sys.exit(166)
        try:
            run_elbe(['control', 'wait_busy', prjdir], check=True)
        except subprocess.CalledProcessError:
            print('elbe control wait_busy Failed', file=sys.stderr)
            print('Giving up', file=sys.stderr)
            sys.exit(167)
        print('')
        print('Pdebuild finished !')
        print('')

        if opt.skip_download:
            print('')
            print('Listing available files:')
            print('')
            try:
                run_elbe(['control', '--pbuilder-only', 'get_files', prjdir], check=True)
            except subprocess.CalledProcessError:
                print('elbe control get_files Failed', file=sys.stderr)
                print('', file=sys.stderr)
                print('dumping logfile', file=sys.stderr)

                try:
                    run_elbe(['control', 'dump_file', prjdir, 'log.txt'], check=True)
                except subprocess.CalledProcessError:
                    print('elbe control dump_file Failed', file=sys.stderr)
                    print('', file=sys.stderr)
                    print('Giving up', file=sys.stderr)

                sys.exit(168)

            print('')
            print(f"Get Files with: 'elbe control get_file {prjdir} <filename>'")
        else:
            print('')
            print('Getting generated Files')
            print('')

            ensure_outdir(opt)

            try:
                run_elbe(['control', '--pbuilder-only', 'get_files',
                          '--output', opt.outdir, prjdir], check=True)
            except subprocess.CalledProcessError:
                print('elbe control get_files Failed', file=sys.stderr)
                print('', file=sys.stderr)
                print('dumping logfile', file=sys.stderr)

                try:
                    run_elbe(['control', 'dump_file', prjdir, 'log.txt'], check=True)
                except subprocess.CalledProcessError:
                    print('elbe control dump_file Failed', file=sys.stderr)
                    print('', file=sys.stderr)
                    print('Giving up', file=sys.stderr)

                sys.exit(169)


PBuilderAction.register(BuildAction)
