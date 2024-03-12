# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2015-2018 Linutronix GmbH
# SPDX-FileCopyrightText: 2015 Silvio Fricke <silvio.fricke@gmail.com>

import datetime
import io
import os
import subprocess
import sys
import time

import elbepack
from elbepack.config import cfg
from elbepack.directories import elbe_exe
from elbepack.elbexml import ElbeXML, ValidationError, ValidationMode
from elbepack.filesystem import TmpdirFilesystem
from elbepack.repodir import Repodir, RepodirError
from elbepack.shellhelper import command_out_stderr, system
from elbepack.treeutils import etree
from elbepack.xmlpreprocess import PreprocessWrapper


def is_soap_local():
    return cfg['soaphost'] in ('localhost', '127.0.0.1')


def cmd_exists(x):
    return any(os.access(os.path.join(path, x), os.X_OK)
               for path in os.environ['PATH'].split(os.pathsep))

# Create download directory with timestamp,
# if necessary


def ensure_outdir(opt):
    if opt.outdir is None:
        opt.outdir = (
            f"elbe-build-{datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}")

    print(f'Saving generated Files to {opt.outdir}')


class InitVMError(Exception):
    def __init__(self, msg):
        Exception.__init__(self, msg)


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

    def __new__(cls, node):
        action = cls.actiondict[node]
        return object.__new__(action)

    def __init__(self, node, initvmNeeded=True):

        self.initvm = None
        self.conn = None
        self.node = node

        # initvm might be running on a different host.  Thus there's
        # no need to talk with libvirt
        if not is_soap_local():
            return

        import libvirt

        # The tag initvmNeeded is required in order to be able to run `elbe
        # initvm create`
        try:
            self.conn = libvirt.open('qemu:///system')
        except libvirt.libvirtError as verr:
            if not isinstance(verr.args[0], str):
                raise
            if verr.args[0].startswith('Failed to connect socket to'):
                retries = 18
                while retries > 0:
                    retries -= 1
                    time.sleep(10)
                    try:
                        self.conn = libvirt.open('qemu:///system')
                    except libvirt.libvirtError as verr:
                        if not isinstance(verr.args[0], str):
                            raise
                        if verr.args[0].startswith('Failed to connect socket to'):
                            pass

                    if self.conn:
                        break

                if not self.conn:
                    print('', file=sys.stderr)
                    print('Accessing libvirt provider system not possible.', file=sys.stderr)
                    print('Even after waiting 180 seconds.', file=sys.stderr)
                    print("Make sure that package 'libvirt-daemon-system' is", file=sys.stderr)
                    print('installed, and the service is running properly', file=sys.stderr)
                    sys.exit(118)

            elif verr.args[0].startswith('authentication unavailable'):
                print('', file=sys.stderr)
                print('Accessing libvirt provider system not allowed.', file=sys.stderr)
                print('Users which want to use elbe'
                      "need to be members of the 'libvirt' group.", file=sys.stderr)
                print("'gpasswd -a <user> libvirt' and logging in again,", file=sys.stderr)
                print('should fix the problem.', file=sys.stderr)
                sys.exit(119)

            elif verr.args[0].startswith('error from service: CheckAuthorization'):
                print('', file=sys.stderr)
                print('Accessing libvirt failed.', file=sys.stderr)
                print('Probably entering the password for accssing libvirt', file=sys.stderr)
                print("timed out. If this occured after 'elbe initvm create'", file=sys.stderr)
                print("it should be safe to use 'elbe initvm start' to", file=sys.stderr)
                print('continue.', file=sys.stderr)
                sys.exit(120)

            else:
                # In case we get here, the exception is unknown, and we want to see it
                raise

        doms = self.conn.listAllDomains()

        for d in doms:
            if d.name() == cfg['initvm_domain']:
                self.initvm = d

        if not self.initvm and initvmNeeded:
            sys.exit(121)

    def execute(self, _initvmdir, _opt, _args):
        raise NotImplementedError('execute() not implemented')

    def initvm_state(self):
        return self.initvm.info()[0]


@InitVMAction.register('start')
class StartAction(InitVMAction):

    def __init__(self, node):
        InitVMAction.__init__(self, node)

    def _attach_disk_fds(self):
        # libvirt does not necessarily have permissions to directly access the
        # image file. libvirt 9.0 provides FDAssociate() to pass an open file
        # descriptor to libvirt which is used to access files via the context
        # of the client, which has permissions.

        if not hasattr(self.initvm, 'FDAssociate'):
            return

        xml = etree(io.StringIO(self.initvm.XMLDesc()))
        disk = xml.et.find('/devices/disk')

        for source in disk.findall('.//source'):
            flags = os.O_RDWR if source.getparent() is disk else os.O_RDONLY
            # Use raw unmanaged FDs as libvirt will take full ownership of them.
            self.initvm.FDAssociate(source.attrib['fdgroup'], [
                os.open(source.attrib['file'], flags),
            ])

    def execute(self, _initvmdir, _opt, _args):
        import libvirt

        if self.initvm_state() == libvirt.VIR_DOMAIN_RUNNING:
            print('Initvm already running.')
            sys.exit(122)
        elif self.initvm_state() == libvirt.VIR_DOMAIN_SHUTOFF:
            self._attach_disk_fds()

            # Domain is shut off. Let's start it!
            self.initvm.create()
            # Wait five seconds for the initvm to boot
            # TODO: Instead of waiting for five seconds
            # check whether SOAP server is reachable.
            for _ in range(1, 5):
                sys.stdout.write('*')
                sys.stdout.flush()
                time.sleep(1)
            print('*')


@InitVMAction.register('ensure')
class EnsureAction(InitVMAction):

    def __init__(self, node):
        InitVMAction.__init__(self, node)

    def execute(self, _initvmdir, _opt, _args):

        # initvm might be running on a different host, thus skipping
        # the check
        if not is_soap_local():
            return

        import libvirt

        if self.initvm_state() == libvirt.VIR_DOMAIN_SHUTOFF:
            system(f'{sys.executable} {elbe_exe} initvm start')
        elif self.initvm_state() == libvirt.VIR_DOMAIN_RUNNING:
            stop = time.time() + 300
            while True:
                cmd = command_out_stderr(f'{sys.executable} {elbe_exe} control list_projects')
                if cmd[0] == 0:
                    break
                if time.time() > stop:
                    print(f'Waited for 5 minutes and the daemon is still not active: {cmd[2]}',
                          file=sys.stderr)
                    sys.exit(123)
                time.sleep(10)
        else:
            print('Elbe initvm in bad state.')
            sys.exit(124)


@InitVMAction.register('stop')
class StopAction(InitVMAction):

    def __init__(self, node):
        InitVMAction.__init__(self, node)

    def execute(self, _initvmdir, _opt, _args):
        import libvirt

        if self.initvm_state() != libvirt.VIR_DOMAIN_RUNNING:
            print('Initvm is not running.')
            sys.exit(125)

        while True:

            sys.stdout.write('*')
            sys.stdout.flush()
            time.sleep(1)

            state = self.initvm_state()

            if state == libvirt.VIR_DOMAIN_SHUTDOWN:
                continue

            if state == libvirt.VIR_DOMAIN_SHUTOFF:
                break

            try:
                self.initvm.shutdown()
            except libvirt.libvirtError as e:
                raise e

        print('\nInitvm shutoff')


@InitVMAction.register('attach')
class AttachAction(InitVMAction):

    def __init__(self, node):
        InitVMAction.__init__(self, node)

    def execute(self, _initvmdir, _opt, _args):
        import libvirt

        if self.initvm_state() != libvirt.VIR_DOMAIN_RUNNING:
            print('Error: Initvm not running properly.')
            sys.exit(126)

        print('Attaching to initvm console.')
        system(f'virsh --connect qemu:///system console {cfg["initvm_domain"]}')


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

    try:
        with PreprocessWrapper(xmlfile, opt) as ppw:
            xmlfile = ppw.preproc

            ret, prjdir, err = command_out_stderr(
                f'{sys.executable} {elbe_exe} control create_project')
            if ret != 0:
                print('elbe control create_project failed.', file=sys.stderr)
                print(err, file=sys.stderr)
                print('Giving up', file=sys.stderr)
                sys.exit(128)

            prjdir = prjdir.strip()

            cmd = f'{sys.executable} {elbe_exe} control set_xml {prjdir} {xmlfile}'
            ret, _, err = command_out_stderr(cmd)
            if ret != 0:
                print('elbe control set_xml failed2', file=sys.stderr)
                print(err, file=sys.stderr)
                print('Giving up', file=sys.stderr)
                sys.exit(129)
    except subprocess.CalledProcessError:
        # this is the failure from PreprocessWrapper
        # it already printed the error message from
        # elbe preprocess
        print('Giving up', file=sys.stderr)
        sys.exit(130)

    if opt.writeproject:
        with open(opt.writeproject, 'w') as wpf:
            wpf.write(prjdir)

    if cdrom is not None:
        print('Uploading CDROM. This might take a while')
        try:
            system(f'{sys.executable} {elbe_exe} control set_cdrom "{prjdir}" "{cdrom}"')
        except subprocess.CalledProcessError:
            print('elbe control set_cdrom Failed', file=sys.stderr)
            print('Giving up', file=sys.stderr)
            sys.exit(131)

        print('Upload finished')

    build_opts = ''
    if opt.build_bin:
        build_opts += '--build-bin '
    if opt.build_sources:
        build_opts += '--build-sources '
    if cdrom:
        build_opts += '--skip-pbuilder '

    try:
        system(f'{sys.executable} {elbe_exe} control build "{prjdir}" {build_opts}')
    except subprocess.CalledProcessError:
        print('elbe control build Failed', file=sys.stderr)
        print('Giving up', file=sys.stderr)
        sys.exit(132)

    print('Build started, waiting till it finishes')

    try:
        system(f'{sys.executable} {elbe_exe} control wait_busy "{prjdir}"')
    except subprocess.CalledProcessError:
        print('elbe control wait_busy Failed', file=sys.stderr)
        print('', file=sys.stderr)
        print('The project will not be deleted from the initvm.',
              file=sys.stderr)
        print('The files, that have been built, can be downloaded using:',
              file=sys.stderr)
        print(
            f'{elbe_exe} control get_files --output "{opt.outdir}" "{prjdir}"',
            file=sys.stderr)
        print('', file=sys.stderr)
        print('The project can then be removed using:',
              file=sys.stderr)
        print(f'{elbe_exe} control del_project "{prjdir}"',
              file=sys.stderr)
        print('', file=sys.stderr)
        sys.exit(133)

    print('')
    print('Build finished !')
    print('')

    if opt.build_sdk:
        try:
            system(f'{sys.executable} {elbe_exe} control build_sdk "{prjdir}" {build_opts}')
        except subprocess.CalledProcessError:
            print('elbe control build_sdk Failed', file=sys.stderr)
            print('Giving up', file=sys.stderr)
            sys.exit(134)

        print('SDK Build started, waiting till it finishes')

        try:
            system(f'{sys.executable} {elbe_exe} control wait_busy "{prjdir}"')
        except subprocess.CalledProcessError:
            print('elbe control wait_busy Failed, while waiting for the SDK',
                  file=sys.stderr)
            print('', file=sys.stderr)
            print('The project will not be deleted from the initvm.',
                  file=sys.stderr)
            print('The files, that have been built, can be downloaded using:',
                  file=sys.stderr)
            print(
                f'{elbe_exe} control get_files --output "{opt.outdir}" '
                f'"{prjdir}"',
                file=sys.stderr)
            print('', file=sys.stderr)
            print('The project can then be removed using:',
                  file=sys.stderr)
            print(f'{elbe_exe} control del_project "{prjdir}"',
                  file=sys.stderr)
            print('', file=sys.stderr)
            sys.exit(135)

        print('')
        print('SDK Build finished !')
        print('')

    try:
        system(f'{sys.executable} {elbe_exe} control dump_file "{prjdir}" validation.txt')
    except subprocess.CalledProcessError:
        print(
            'Project failed to generate validation.txt',
            file=sys.stderr)
        print('Getting log.txt', file=sys.stderr)
        try:
            system(f'{sys.executable} {elbe_exe} control dump_file "{prjdir}" log.txt')
        except subprocess.CalledProcessError:

            print('Failed to dump log.txt', file=sys.stderr)
            print('Giving up', file=sys.stderr)
        sys.exit(136)

    if opt.skip_download:
        print('')
        print('Listing available files:')
        print('')
        try:
            system(f'{sys.executable} {elbe_exe} control get_files "{prjdir}"')
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

        ensure_outdir(opt)

        try:
            system(
                f'{sys.executable} {elbe_exe} control get_files --output "{opt.outdir}" '
                f'"{prjdir}"')
        except subprocess.CalledProcessError:
            print('elbe control get_files Failed', file=sys.stderr)
            print('Giving up', file=sys.stderr)
            sys.exit(138)

        if not opt.keep_files:
            try:
                system(f'{sys.executable} {elbe_exe} control del_project "{prjdir}"')
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
        system(f'7z x -o{tmp.path} "{cdrom}" {in_iso_name}')

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

    def __init__(self, node):
        InitVMAction.__init__(self, node, initvmNeeded=False)

    def execute(self, initvmdir, opt, args):

        if self.initvm is not None:
            print(f"Initvm is already defined for the libvirt domain '{cfg['initvm_domain']}'.\n")
            print('If you want to build in your old initvm, use `elbe initvm submit <xml>`.')
            print('If you want to remove your old initvm from libvirt '
                  f"run `virsh --connect qemu:///system undefine {cfg['initvm_domain']}`.\n")
            print('You can specify another libvirt domain by setting the '
                  'ELBE_INITVM_DOMAIN environment variable to an unused domain name.\n')
            print('Note:')
            print('\t1) You can reimport your old initvm via '
                  '`virsh --connect qemu:///system define <file>`')
            print('\t   where <file> is the corresponding libvirt.xml')
            print('\t2) virsh --connect qemu:///system undefine does not delete the image '
                  'of your old initvm.')
            sys.exit(142)

        # Upgrade from older versions which used tmux
        try:
            system('tmux has-session -t ElbeInitVMSession 2>/dev/null')
            print('ElbeInitVMSession exists in tmux. '
                  'It may belong to an old elbe version. '
                  'Please stop it to prevent interfering with this version.', file=sys.stderr)
            sys.exit(143)
        except subprocess.CalledProcessError:
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
            init_opts = ''
            if opt.devel:
                init_opts += ' --devel'

            if opt.nesting:
                init_opts += ' --nesting'

            if not opt.build_bin:
                init_opts += ' --skip-build-bin'

            if not opt.build_sources:
                init_opts += ' --skip-build-source'

            with PreprocessWrapper(xmlfile, opt) as ppw:
                if cdrom:
                    system(
                        f'{sys.executable} {elbe_exe} init {init_opts} '
                        f'--directory "{initvmdir}" --cdrom "{cdrom}" '
                        f'"{ppw.preproc}"')
                else:
                    system(
                        f'{sys.executable} {elbe_exe} init {init_opts} '
                        f'--directory "{initvmdir}" "{ppw.preproc}"')

        except subprocess.CalledProcessError:
            print("'elbe init' Failed", file=sys.stderr)
            print('Giving up', file=sys.stderr)
            sys.exit(145)

        # Read xml file for libvirt
        with open(os.path.join(initvmdir, 'libvirt.xml')) as f:
            xml = f.read()

        # Register initvm in libvirt
        try:
            self.conn.defineXML(xml)
        except subprocess.CalledProcessError:
            print('Registering initvm in libvirt failed', file=sys.stderr)
            print(f"Try `virsh --connect qemu:///system undefine {cfg['initvm_domain']}`"
                  'to delete existing initvm',
                  file=sys.stderr)
            sys.exit(146)

        # Build initvm
        try:
            system(f'cd "{initvmdir}"; make')
        except subprocess.CalledProcessError:
            print('Building the initvm Failed', file=sys.stderr)
            print('Giving up', file=sys.stderr)
            sys.exit(147)

        try:
            system(f'{sys.executable} {elbe_exe} initvm start')
        except subprocess.CalledProcessError:
            print('Starting the initvm Failed', file=sys.stderr)
            print('Giving up', file=sys.stderr)
            sys.exit(148)

        if len(args) == 1:
            # if provided xml file has no initvm section xmlfile is set to a
            # default initvm XML file. But we need the original file here
            if args[0].endswith('.xml'):
                # stop here if no project node was specified
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

    def __init__(self, node):
        InitVMAction.__init__(self, node)

    def execute(self, _initvmdir, opt, args):
        try:
            system(f'{sys.executable} {elbe_exe} initvm ensure')
        except subprocess.CalledProcessError:
            print('Starting the initvm Failed', file=sys.stderr)
            print('Giving up', file=sys.stderr)
            sys.exit(150)

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

    def __init__(self, node):
        super(SyncAction, self).__init__(node)

    def execute(self, _initvmdir, opt, args):
        top_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
        try:
            system('rsync --info=name1,stats1  --archive --times '
                   "--exclude='.git*' --exclude='*.pyc' --exclude='elbe-build*' "
                   "--exclude='initvm' --exclude='__pycache__' --exclude='docs' "
                   "--exclude='examples' "
                   f"--rsh='ssh -p {cfg['sshport']}' --chown=root:root "
                   f'{top_dir}/ root@localhost:/var/cache/elbe/devel')
        except subprocess.CalledProcessError as E:
            print(E)
