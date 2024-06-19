# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2015-2018 Linutronix GmbH
# SPDX-FileCopyrightText: 2015 Silvio Fricke <silvio.fricke@gmail.com>

import os
import subprocess
import sys
import time

import elbepack
import elbepack.initvm
from elbepack.config import cfg
from elbepack.directories import run_elbe
from elbepack.elbexml import ElbeXML, ValidationError, ValidationMode
from elbepack.filesystem import TmpdirFilesystem
from elbepack.repodir import Repodir, RepodirError
from elbepack.treeutils import etree
from elbepack.xmlpreprocess import preprocess_file


prog = os.path.basename(sys.argv[0])


class InitVMAction:
    actiondict = {}

    @classmethod
    def register(cls, tag):
        def _register(action):
            action.tag = tag
            cls.actiondict[action.tag] = action
            return action
        return _register

    @classmethod
    def print_actions(cls):
        print('available subcommands are:', file=sys.stderr)
        for a in cls.actiondict:
            print(f'   {a}', file=sys.stderr)

    @classmethod
    def get_action_class(cls, name):
        return cls.actiondict[name]

    def __init__(self, directory, opt):
        self.directory = directory
        if opt.qemu_mode:
            self.initvm = elbepack.initvm.QemuInitVM(directory=directory)
        else:
            self.initvm = elbepack.initvm.LibvirtInitVM(directory=directory,
                                                        domain=cfg['initvm_domain'])

    def execute(self, opt, args):
        raise NotImplementedError('execute() not implemented')


@InitVMAction.register('start')
class StartAction(InitVMAction):
    def execute(self, opt, args):
        self.initvm.start()


@InitVMAction.register('ensure')
class EnsureAction(InitVMAction):
    def execute(self, opt, args):
        self.initvm.ensure()


@InitVMAction.register('stop')
class StopAction(InitVMAction):
    def execute(self, opt, args):
        self.initvm.stop()


@InitVMAction.register('destroy')
class DestroyAction(InitVMAction):
    def execute(self, opt, _args):
        self.initvm.destroy()


@InitVMAction.register('attach')
class AttachAction(InitVMAction):
    def execute(self, opt, args):
        self.initvm.attach()


def submit_with_repodir_and_dl_result(xmlfile, cdrom, opt):
    fname = f'elbe-repodir-{time.time_ns()}.xml'
    preprocess_xmlfile = os.path.join(os.path.dirname(xmlfile), fname)
    try:
        with Repodir(xmlfile, preprocess_xmlfile):
            submit_and_dl_result(preprocess_xmlfile, cdrom, opt)
    except RepodirError as err:
        print('elbe repodir failed', file=sys.stderr)
        print(err, file=sys.stderr)
        sys.exit(127)
    finally:
        os.remove(preprocess_xmlfile)


def submit_and_dl_result(xmlfile, cdrom, opt):

    with preprocess_file(xmlfile, opt.variants) as xmlfile:

        ps = run_elbe(['control', 'create_project'], capture_output=True, encoding='utf-8')
        if ps.returncode != 0:
            print('elbe control create_project failed.', file=sys.stderr)
            print(ps.stderr, file=sys.stderr)
            print('Giving up', file=sys.stderr)
            sys.exit(128)

        prjdir = ps.stdout.strip()

        ps = run_elbe(['control', 'set_xml', prjdir, xmlfile],
                      capture_output=True, encoding='utf-8')
        if ps.returncode != 0:
            print('elbe control set_xml failed2', file=sys.stderr)
            print(ps.stderr, file=sys.stderr)
            print('Giving up', file=sys.stderr)
            sys.exit(129)

    if opt.writeproject:
        with open(opt.writeproject, 'w') as wpf:
            wpf.write(prjdir)

    if cdrom is not None:
        print('Uploading CDROM. This might take a while')
        try:
            run_elbe(['control', 'set_cdrom', prjdir, cdrom], check=True)
        except subprocess.CalledProcessError:
            print('elbe control set_cdrom Failed', file=sys.stderr)
            print('Giving up', file=sys.stderr)
            sys.exit(131)

        print('Upload finished')

    build_opts = []
    if opt.build_bin:
        build_opts.append('--build-bin')
    if opt.build_sources:
        build_opts.append('--build-sources')
    if cdrom:
        build_opts.append('--skip-pbuilder')

    try:
        run_elbe(['control', 'build', prjdir, *build_opts], check=True)
    except subprocess.CalledProcessError:
        print('elbe control build Failed', file=sys.stderr)
        print('Giving up', file=sys.stderr)
        sys.exit(132)

    print('Build started, waiting till it finishes')

    try:
        run_elbe(['control', 'wait_busy', prjdir], check=True)
    except subprocess.CalledProcessError:
        print('elbe control wait_busy Failed', file=sys.stderr)
        print('', file=sys.stderr)
        print('The project will not be deleted from the initvm.',
              file=sys.stderr)
        print('The files, that have been built, can be downloaded using:',
              file=sys.stderr)
        print(
            f'{prog} control get_files --output "{opt.outdir}" "{prjdir}"',
            file=sys.stderr)
        print('', file=sys.stderr)
        print('The project can then be removed using:',
              file=sys.stderr)
        print(f'{prog} control del_project "{prjdir}"',
              file=sys.stderr)
        print('', file=sys.stderr)
        sys.exit(133)

    print('')
    print('Build finished !')
    print('')

    if opt.build_sdk:
        try:
            run_elbe(['control', 'build_sdk', prjdir], check=True)
        except subprocess.CalledProcessError:
            print('elbe control build_sdk Failed', file=sys.stderr)
            print('Giving up', file=sys.stderr)
            sys.exit(134)

        print('SDK Build started, waiting till it finishes')

        try:
            run_elbe(['control', 'wait_busy', prjdir], check=True)
        except subprocess.CalledProcessError:
            print('elbe control wait_busy Failed, while waiting for the SDK',
                  file=sys.stderr)
            print('', file=sys.stderr)
            print('The project will not be deleted from the initvm.',
                  file=sys.stderr)
            print('The files, that have been built, can be downloaded using:',
                  file=sys.stderr)
            print(
                f'{prog} control get_files --output "{opt.outdir}" '
                f'"{prjdir}"',
                file=sys.stderr)
            print('', file=sys.stderr)
            print('The project can then be removed using:',
                  file=sys.stderr)
            print(f'{prog} control del_project "{prjdir}"',
                  file=sys.stderr)
            print('', file=sys.stderr)
            sys.exit(135)

        print('')
        print('SDK Build finished !')
        print('')

    try:
        run_elbe(['control', 'dump_file', prjdir, 'validation.txt'], check=True)
    except subprocess.CalledProcessError:
        print(
            'Project failed to generate validation.txt',
            file=sys.stderr)
        print('Getting log.txt', file=sys.stderr)
        try:
            run_elbe(['control', 'dump_file', prjdir, 'log.txt'], check=True)
        except subprocess.CalledProcessError:

            print('Failed to dump log.txt', file=sys.stderr)
            print('Giving up', file=sys.stderr)
        sys.exit(136)

    if opt.skip_download:
        print('')
        print('Listing available files:')
        print('')
        try:
            run_elbe(['control', 'get_files', prjdir], check=True)
        except subprocess.CalledProcessError:
            print('elbe control get_files Failed', file=sys.stderr)
            print('Giving up', file=sys.stderr)
            sys.exit(137)

        print('')
        print(f'Get Files with: elbe control get_file "{prjdir}" <filename>')
    else:
        print('')
        print('Getting generated Files')
        print('')

        print(f'Saving generated Files to {opt.outdir}')

        try:
            run_elbe(['control', 'get_files', '--output', opt.outdir, prjdir], check=True)
        except subprocess.CalledProcessError:
            print('elbe control get_files Failed', file=sys.stderr)
            print('Giving up', file=sys.stderr)
            sys.exit(138)

        if not opt.keep_files:
            try:
                run_elbe(['control', 'del_project', prjdir], check=True)
            except subprocess.CalledProcessError:
                print('remove project from initvm failed',
                      file=sys.stderr)
                sys.exit(139)


def extract_cdrom(cdrom):
    """ Extract cdrom iso image
        returns a TmpdirFilesystem() object containing
        the source.xml, which is also validated.
    """

    tmp = TmpdirFilesystem()
    in_iso_name = 'source.xml'
    try:
        import pycdlib
        iso = pycdlib.PyCdlib()
        iso.open(cdrom)
        extracted = os.path.join(tmp.path, in_iso_name)
        iso.get_file_from_iso(extracted, iso_path=f'/{in_iso_name.upper()};1')
        iso.close()
    except ImportError:
        subprocess.run(['7z', 'x', f'-o{tmp.path}', cdrom, in_iso_name], check=True)

    print('', file=sys.stderr)

    if not tmp.isfile('source.xml'):
        print(
            'Iso image does not contain a source.xml file',
            file=sys.stderr)
        print(
            "This is not supported by 'elbe initvm'",
            file=sys.stderr)
        print('', file=sys.stderr)
        print('Exiting !!!', file=sys.stderr)
        sys.exit(140)

    try:
        exml = ElbeXML(
            tmp.fname('source.xml'),
            url_validation=ValidationMode.NO_CHECK)
    except ValidationError as e:
        print(
            'Iso image does contain a source.xml file.',
            file=sys.stderr)
        print(
            'But that xml does not validate correctly',
            file=sys.stderr)
        print('', file=sys.stderr)
        print('Exiting !!!', file=sys.stderr)
        print(e)
        sys.exit(141)

    print('Iso Image with valid source.xml detected !')
    print(f'Image was generated using Elbe Version {exml.get_elbe_version()}')

    return tmp


@InitVMAction.register('create')
class CreateAction(InitVMAction):
    def execute(self, opt, args):
        # Upgrade from older versions which used tmux
        try:
            subprocess.run(['tmux', 'has-session', '-t', 'ElbeInitVMSession'],
                           stderr=subprocess.DEVNULL, check=True)
            print('ElbeInitVMSession exists in tmux. '
                  'It may belong to an old elbe version. '
                  'Please stop it to prevent interfering with this version.', file=sys.stderr)
            sys.exit(143)
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass

        # Init cdrom to None, if we detect it, we set it
        cdrom = None

        if len(args) == 1:
            if args[0].endswith('.xml'):
                # We have an xml file, use that for elbe init
                xmlfile = args[0]
                try:
                    xml = etree(xmlfile)
                except ValidationError as e:
                    print(f'XML file is invalid: {e}')
                # Use default XML if no initvm was specified
                if not xml.has('initvm'):
                    xmlfile = os.path.join(
                        elbepack.__path__[0], 'init/default-init.xml')

            elif args[0].endswith('.iso'):
                # We have an iso image, extract xml from there.
                tmp = extract_cdrom(args[0])

                xmlfile = tmp.fname('source.xml')
                cdrom = args[0]
            else:
                print(
                    'Unknown file ending (use either xml or iso)',
                    file=sys.stderr)
                sys.exit(144)
        else:
            # No xml File was specified, build the default elbe-init-with-ssh
            xmlfile = os.path.join(
                elbepack.__path__[0],
                'init/default-init.xml')

        try:
            init_opts = []

            if not opt.build_bin:
                init_opts.append('--skip-build-bin')

            if not opt.build_sources:
                init_opts.append('--skip-build-source')

            if opt.fail_on_warning:
                init_opts.append('--fail-on-warning')

            if cdrom:
                cdrom_opts = ['--cdrom', cdrom]
            else:
                cdrom_opts = []

            with preprocess_file(xmlfile, opt.variants) as preproc:
                run_elbe(['init', *init_opts, '--directory', self.directory, *cdrom_opts, preproc],
                         check=True)

        except subprocess.CalledProcessError:
            print("'elbe init' Failed", file=sys.stderr)
            print('Giving up', file=sys.stderr)
            sys.exit(145)

        self.initvm._build()
        self.initvm.start()

        if len(args) == 1:
            # If provided xml file has no initvm section xmlfile is set to a
            # default initvm XML file. But we need the original file here.
            if args[0].endswith('.xml'):
                # Stop here if no project node was specified.
                try:
                    x = etree(args[0])
                except ValidationError as e:
                    print(f'XML file is invalid: {e}')
                    sys.exit(149)
                if not x.has('project'):
                    print("elbe initvm ready: use 'elbe initvm submit "
                          "myproject.xml' to build a project")
                    sys.exit(0)

                xmlfile = args[0]
            elif cdrom is not None:
                xmlfile = tmp.fname('source.xml')

            submit_with_repodir_and_dl_result(xmlfile, cdrom, opt)


@InitVMAction.register('submit')
class SubmitAction(InitVMAction):

    def execute(self, opt, args):
        self.initvm.ensure()

        # Init cdrom to None, if we detect it, we set it
        cdrom = None

        if len(args) == 1:
            if args[0].endswith('.xml'):
                # We have an xml file, use that for elbe init
                xmlfile = args[0]
            elif args[0].endswith('.iso'):
                # We have an iso image, extract xml from there.
                tmp = extract_cdrom(args[0])

                xmlfile = tmp.fname('source.xml')
                cdrom = args[0]
            else:
                print(
                    'Unknown file ending (use either xml or iso)',
                    file=sys.stderr)
                sys.exit(151)

            submit_with_repodir_and_dl_result(xmlfile, cdrom, opt)


@InitVMAction.register('sync')
class SyncAction(InitVMAction):

    def execute(self, _opt, _args):
        top_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
        excludes = ['.git*', '*.pyc', 'elbe-build*', 'initvm', '__pycache__', 'docs', 'examples']
        ssh = ['ssh', '-p', cfg['sshport'], '-oUserKnownHostsFile=/dev/null']
        try:
            subprocess.run([
                'rsync', '--info=name1,stats1', '--archive', '--times',
                *[arg for e in excludes for arg in ('--exclude', e)],
                '--rsh', ' '.join(ssh),
                '--chown=root:root',
                f'{top_dir}/elbe',
                f'{top_dir}/elbepack',
                'root@localhost:/var/cache/elbe/devel'
            ], check=True)
            subprocess.run([
                *ssh, 'root@localhost', 'systemctl', 'restart', 'python3-elbe-daemon',
            ], check=True)
        except subprocess.CalledProcessError as E:
            print(E)
