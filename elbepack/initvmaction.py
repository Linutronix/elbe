# ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (c) 2015-2017 Manuel Traut <manut@linutronix.de>
# Copyright (c) 2015-2018 Torben Hohn <torben.hohn@linutronix.de>
# Copyright (c) 2015 Silvio Fricke <silvio.fricke@gmail.com>
# Copyright (c) 2017 Philipp Arras <philipp.arras@linutronix.de>
# Copyright (c) 2017 Benedikt Spranger <b.spranger@linutronix.de>
# Copyright (c) 2017 John Ogness <john.ogness@linutronix.de>
#
# SPDX-License-Identifier: GPL-3.0-or-later

import sys
import time
import os
import datetime

import elbepack
from elbepack.treeutils import etree
from elbepack.directories import elbe_exe
from elbepack.shellhelper import CommandError, system, command_out_stderr, \
                                 command_out
from elbepack.filesystem import TmpdirFilesystem
from elbepack.elbexml import ElbeXML, ValidationError, ValidationMode
from elbepack.config import cfg
from elbepack.repodir import RepodirError, Repodir
from elbepack.xmlpreprocess import PreprocessWrapper

def is_soap_local():
    return cfg["soaphost"] in ("localhost", "127.0.0.1")

def cmd_exists(x):
    return any(os.access(os.path.join(path, x), os.X_OK)
            for path in os.environ["PATH"].split(os.pathsep))

# Create download directory with timestamp,
# if necessary


def ensure_outdir(opt):
    if opt.outdir is None:
        opt.outdir = (
            f"elbe-build-{datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}")

    print(f"Saving generated Files to {opt.outdir}")


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
        print("available subcommands are:", file=sys.stderr)
        for a in cls.actiondict:
            print(f"   {a}", file=sys.stderr)

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
            self.conn = libvirt.open("qemu:///system")
        except libvirt.libvirtError as verr:
            if not isinstance(verr.args[0], str):
                raise
            if verr.args[0].startswith('Failed to connect socket to'):
                retries = 18
                while retries > 0:
                    retries -= 1
                    time.sleep(10)
                    try:
                        self.conn = libvirt.open("qemu:///system")
                    except libvirt.libvirtError as verr:
                        if not isinstance(verr.args[0], str):
                            raise
                        if verr.args[0].startswith('Failed to connect socket to'):
                            pass

                    if self.conn:
                        break


                if not self.conn:
                    print("", file=sys.stderr)
                    print("Accessing libvirt provider system not possible.", file=sys.stderr)
                    print("Even after waiting 180 seconds.", file=sys.stderr)
                    print("Make sure that package 'libvirt-daemon-system' is", file=sys.stderr)
                    print("installed, and the service is running properly", file=sys.stderr)
                    sys.exit(20)

            elif verr.args[0].startswith('authentication unavailable'):
                print("", file=sys.stderr)
                print("Accessing libvirt provider system not allowed.", file=sys.stderr)
                print("Users which want to use elbe need to be members of the 'libvirt' group.", file=sys.stderr)
                print("'gpasswd -a <user> libvirt' and logging in again,", file=sys.stderr)
                print("should fix the problem.", file=sys.stderr)
                sys.exit(20)

            elif verr.args[0].startswith('error from service: CheckAuthorization'):
                print("", file=sys.stderr)
                print("Accessing libvirt failed.", file=sys.stderr)
                print("Probably entering the password for accssing libvirt", file=sys.stderr)
                print("timed out. If this occured after 'elbe initvm create'", file=sys.stderr)
                print("it should be safe to use 'elbe initvm start' to", file=sys.stderr)
                print("continue.", file=sys.stderr)
                sys.exit(20)

            else:
                # In case we get here, the exception is unknown, and we want to see it
                raise

        doms = self.conn.listAllDomains()

        for d in doms:
            if d.name() == cfg['initvm_domain']:
                self.initvm = d

        if not self.initvm and initvmNeeded:
            sys.exit(20)


    def execute(self, _initvmdir, _opt, _args):
        raise NotImplementedError('execute() not implemented')

    def initvm_state(self):
        return self.initvm.info()[0]


@InitVMAction.register('start')
class StartAction(InitVMAction):

    def __init__(self, node):
        InitVMAction.__init__(self, node)

    def execute(self, _initvmdir, _opt, _args):
        import libvirt

        if self.initvm_state() == libvirt.VIR_DOMAIN_RUNNING:
            print('Initvm already running.')
            sys.exit(20)
        elif self.initvm_state() == libvirt.VIR_DOMAIN_SHUTOFF:
            # Domain is shut off. Let's start it!
            self.initvm.create()
            # Wait five seconds for the initvm to boot
            # TODO: Instead of waiting for five seconds
            # check whether SOAP server is reachable.
            for _ in range(1, 5):
                sys.stdout.write("*")
                sys.stdout.flush()
                time.sleep(1)
            print("*")


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
                    print(f"Waited for 5 minutes and the daemon is still not active: {cmd[2]}",
                          file=sys.stderr)
                    sys.exit(20)
                time.sleep(10)
        else:
            print("Elbe initvm in bad state.")
            sys.exit(20)



@InitVMAction.register('stop')
class StopAction(InitVMAction):

    def __init__(self, node):
        InitVMAction.__init__(self, node)

    def execute(self, _initvmdir, _opt, _args):
        import libvirt

        if self.initvm_state() != libvirt.VIR_DOMAIN_RUNNING:
            print('Initvm is not running.')
            sys.exit(20)

        while True:

            sys.stdout.write("*")
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

        print("\nInitvm shutoff")


@InitVMAction.register('attach')
class AttachAction(InitVMAction):

    def __init__(self, node):
        InitVMAction.__init__(self, node)

    def execute(self, _initvmdir, _opt, _args):
        import libvirt

        if self.initvm_state() != libvirt.VIR_DOMAIN_RUNNING:
            print('Error: Initvm not running properly.')
            sys.exit(20)

        print('Attaching to initvm console.')
        system(f'virsh --connect qemu:///system console {cfg["initvm_domain"]}')



def submit_with_repodir_and_dl_result(xmlfile, cdrom, opt):
    fname = f'elbe-repodir-{time.time_ns()}.xml'
    preprocess_xmlfile = os.path.join(os.path.dirname(xmlfile), fname)
    try:
        with Repodir(xmlfile, preprocess_xmlfile):
            submit_and_dl_result(preprocess_xmlfile, cdrom, opt)
    except RepodirError as err:
        print("elbe repodir failed", file=sys.stderr)
        print(err, file=sys.stderr)
        sys.exit(20)
    finally:
        os.remove(preprocess_xmlfile)


def submit_and_dl_result(xmlfile, cdrom, opt):

    # pylint: disable=too-many-statements
    # pylint: disable=too-many-branches

    try:
        with PreprocessWrapper(xmlfile, opt) as ppw:
            xmlfile = ppw.preproc

            ret, prjdir, err = command_out_stderr(
                f'{sys.executable} {elbe_exe} control create_project')
            if ret != 0:
                print("elbe control create_project failed.", file=sys.stderr)
                print(err, file=sys.stderr)
                print("Giving up", file=sys.stderr)
                sys.exit(20)

            prjdir = prjdir.strip()

            cmd = f'{sys.executable} {elbe_exe} control set_xml {prjdir} {xmlfile}'
            ret, _, err = command_out_stderr(cmd)
            if ret != 0:
                print("elbe control set_xml failed2", file=sys.stderr)
                print(err, file=sys.stderr)
                print("Giving up", file=sys.stderr)
                sys.exit(20)
    except CommandError:
        # this is the failure from PreprocessWrapper
        # it already printed the error message from
        # elbe preprocess
        print("Giving up", file=sys.stderr)
        sys.exit(20)

    if opt.writeproject:
        with open(opt.writeproject, "w") as wpf:
            wpf.write(prjdir)

    if cdrom is not None:
        print("Uploading CDROM. This might take a while")
        try:
            system(f'{sys.executable} {elbe_exe} control set_cdrom "{prjdir}" "{cdrom}"')
        except CommandError:
            print("elbe control set_cdrom Failed", file=sys.stderr)
            print("Giving up", file=sys.stderr)
            sys.exit(20)

        print("Upload finished")

    build_opts = ''
    if opt.build_bin:
        build_opts += '--build-bin '
    if opt.build_sources:
        build_opts += '--build-sources '
    if cdrom:
        build_opts += '--skip-pbuilder '

    try:
        system(f'{sys.executable} {elbe_exe} control build "{prjdir}" {build_opts}')
    except CommandError:
        print("elbe control build Failed", file=sys.stderr)
        print("Giving up", file=sys.stderr)
        sys.exit(20)

    print("Build started, waiting till it finishes")

    try:
        system(f'{sys.executable} {elbe_exe} control wait_busy "{prjdir}"')
    except CommandError:
        print('elbe control wait_busy Failed', file=sys.stderr)
        print('', file=sys.stderr)
        print('The project will not be deleted from the initvm.',
              file=sys.stderr)
        print('The files, that have been built, can be downloaded using:',
              file=sys.stderr)
        print(
            f'{elbe_exe} control get_files --output "{opt.outdir}" "{prjdir}"',
              file=sys.stderr)
        print("", file=sys.stderr)
        print('The project can then be removed using:',
              file=sys.stderr)
        print(f'{elbe_exe} control del_project "{prjdir}"',
              file=sys.stderr)
        print("", file=sys.stderr)
        sys.exit(10)

    print("")
    print("Build finished !")
    print("")

    if opt.build_sdk:
        try:
            system(f'{sys.executable} {elbe_exe} control build_sdk "{prjdir}" {build_opts}')
        except CommandError:
            print("elbe control build_sdk Failed", file=sys.stderr)
            print("Giving up", file=sys.stderr)
            sys.exit(20)

        print("SDK Build started, waiting till it finishes")

        try:
            system(f'{sys.executable} {elbe_exe} control wait_busy "{prjdir}"')
        except CommandError:
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
            print("", file=sys.stderr)
            print('The project can then be removed using:',
                  file=sys.stderr)
            print(f'{elbe_exe} control del_project "{prjdir}"',
                  file=sys.stderr)
            print("", file=sys.stderr)
            sys.exit(10)

        print("")
        print("SDK Build finished !")
        print("")

    try:
        system(f'{sys.executable} {elbe_exe} control dump_file "{prjdir}" validation.txt')
    except CommandError:
        print(
            "Project failed to generate validation.txt",
            file=sys.stderr)
        print("Getting log.txt", file=sys.stderr)
        try:
            system(f'{sys.executable} {elbe_exe} control dump_file "{prjdir}" log.txt')
        except CommandError:

            print("Failed to dump log.txt", file=sys.stderr)
            print("Giving up", file=sys.stderr)
        sys.exit(20)

    if opt.skip_download:
        print("")
        print("Listing available files:")
        print("")
        try:
            system(f'{sys.executable} {elbe_exe} control get_files "{prjdir}"')
        except CommandError:
            print("elbe control get_files Failed", file=sys.stderr)
            print("Giving up", file=sys.stderr)
            sys.exit(20)

        print("")
        print(f'Get Files with: elbe control get_file "{prjdir}" <filename>')
    else:
        print("")
        print("Getting generated Files")
        print("")

        ensure_outdir(opt)

        try:
            system(
                f'{sys.executable} {elbe_exe} control get_files --output "{opt.outdir}" '
                f'"{prjdir}"')
        except CommandError:
            print("elbe control get_files Failed", file=sys.stderr)
            print("Giving up", file=sys.stderr)
            sys.exit(20)

        if not opt.keep_files:
            try:
                system(f'{sys.executable} {elbe_exe} control del_project "{prjdir}"')
            except CommandError:
                print("remove project from initvm failed",
                      file=sys.stderr)
                sys.exit(20)

def extract_cdrom(cdrom):
    """ Extract cdrom iso image
        returns a TmpdirFilesystem() object containing
        the source.xml, which is also validated.
    """

    tmp = TmpdirFilesystem()
    in_iso_name = "source.xml"
    try:
        import pycdlib
        iso = pycdlib.PyCdlib()
        iso.open(cdrom)
        extracted = os.path.join(tmp.path, in_iso_name)
        iso.get_file_from_iso(extracted, iso_path=f'/{in_iso_name.upper()};1')
        iso.close()
    except ImportError:
        system(f'7z x -o{tmp.path} "{cdrom}" {in_iso_name}')

    print("", file=sys.stderr)

    if not tmp.isfile('source.xml'):
        print(
            "Iso image does not contain a source.xml file",
            file=sys.stderr)
        print(
            "This is not supported by 'elbe initvm'",
            file=sys.stderr)
        print("", file=sys.stderr)
        print("Exiting !!!", file=sys.stderr)
        sys.exit(20)

    try:
        exml = ElbeXML(
            tmp.fname('source.xml'),
            url_validation=ValidationMode.NO_CHECK)
    except ValidationError as e:
        print(
            "Iso image does contain a source.xml file.",
            file=sys.stderr)
        print(
            "But that xml does not validate correctly",
            file=sys.stderr)
        print("", file=sys.stderr)
        print("Exiting !!!", file=sys.stderr)
        print(e)
        sys.exit(20)

    print("Iso Image with valid source.xml detected !")
    print(f"Image was generated using Elbe Version {exml.get_elbe_version()}")

    return tmp


@InitVMAction.register('create')
class CreateAction(InitVMAction):

    def __init__(self, node):
        InitVMAction.__init__(self, node, initvmNeeded=False)

    def execute(self, initvmdir, opt, args):

        # pylint: disable=too-many-branches
        # pylint: disable=too-many-statements

        if self.initvm is not None:
            print(f"Initvm is already defined for the libvirt domain '{cfg['initvm_domain']}'.\n")
            print("If you want to build in your old initvm, use `elbe initvm submit <xml>`.")
            print("If you want to remove your old initvm from libvirt "
                  f"run `virsh --connect qemu:///system undefine {cfg['initvm_domain']}`.\n")
            print("You can specify another libvirt domain by setting the "
                  "ELBE_INITVM_DOMAIN environment variable to an unused domain name.\n")
            print("Note:")
            print("\t1) You can reimport your old initvm via "
                    "`virsh --connect qemu:///system define <file>`")
            print("\t   where <file> is the corresponding libvirt.xml")
            print("\t2) virsh --connect qemu:///system undefine does not delete the image "
                  "of your old initvm.")
            sys.exit(20)

        # Upgrade from older versions which used tmux
        try:
            system("tmux has-session -t ElbeInitVMSession 2>/dev/null")
            print ("ElbeInitVMSession exists in tmux. "
                   "It may belong to an old elbe version. "
                   "Please stop it to prevent interfering with this version.", file=sys.stderr)
            sys.exit(20)
        except CommandError:
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
                    print(f"XML file is invalid: {e}")
                # Use default XML if no initvm was specified
                if not xml.has("initvm"):
                    xmlfile = os.path.join(
                        elbepack.__path__[0], "init/default-init.xml")

            elif args[0].endswith('.iso'):
                # We have an iso image, extract xml from there.
                tmp = extract_cdrom(args[0])

                xmlfile = tmp.fname('source.xml')
                cdrom = args[0]
            else:
                print(
                    "Unknown file ending (use either xml or iso)",
                    file=sys.stderr)
                sys.exit(20)
        else:
            # No xml File was specified, build the default elbe-init-with-ssh
            xmlfile = os.path.join(
                elbepack.__path__[0],
                "init/default-init.xml")

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

            if opt.keys_dir:
                init_opts += f' --keys_dir "{opt.keys_dir}"'

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

        except CommandError:
            print("'elbe init' Failed", file=sys.stderr)
            print("Giving up", file=sys.stderr)
            sys.exit(20)

        # Read xml file for libvirt
        with open(os.path.join(initvmdir, 'libvirt.xml')) as f:
            xml = f.read()

        # Register initvm in libvirt
        try:
            self.conn.defineXML(xml)
        except CommandError:
            print('Registering initvm in libvirt failed', file=sys.stderr)
            print(f"Try `virsh --connect qemu:///system undefine {cfg['initvm_domain']}` to delete existing initvm",
                  file=sys.stderr)
            sys.exit(20)

        # Build initvm
        try:
            system(f'cd "{initvmdir}"; make')
        except CommandError:
            print("Building the initvm Failed", file=sys.stderr)
            print("Giving up", file=sys.stderr)
            sys.exit(20)

        try:
            system(f'{sys.executable} {elbe_exe} initvm start')
        except CommandError:
            print("Starting the initvm Failed", file=sys.stderr)
            print("Giving up", file=sys.stderr)
            sys.exit(20)

        if len(args) == 1:
            # if provided xml file has no initvm section xmlfile is set to a
            # default initvm XML file. But we need the original file here
            if args[0].endswith('.xml'):
                # stop here if no project node was specified
                try:
                    x = etree(args[0])
                except ValidationError as e:
                    print(f"XML file is invalid: {e}")
                    sys.exit(20)
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
        except CommandError:
            print("Starting the initvm Failed", file=sys.stderr)
            print("Giving up", file=sys.stderr)
            sys.exit(20)

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
                    "Unknown file ending (use either xml or iso)",
                    file=sys.stderr)
                sys.exit(20)

            submit_with_repodir_and_dl_result(xmlfile, cdrom, opt)

@InitVMAction.register('sync')
class SyncAction(InitVMAction):

    def __init__(self, node):
        super(SyncAction, self).__init__(node)

    def execute(self, _initvmdir, opt, args):
        top_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
        try:
            system("rsync --info=name1,stats1  --archive --times "
                   "--exclude='.git*' --exclude='*.pyc' --exclude='elbe-build*' "
                   "--exclude='initvm' --exclude='__pycache__' --exclude='docs' "
                   "--exclude='examples' "
                   f"--rsh='ssh -p {cfg['sshport']}' --chown=root:root "
                   f"{top_dir}/ root@localhost:/var/cache/elbe/devel")
        except CommandError as E:
            print(E)
