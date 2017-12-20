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

from __future__ import print_function

import elbepack
from elbepack.treeutils import etree
from elbepack.directories import elbe_exe
from elbepack.shellhelper import CommandError, system, command_out_stderr
from elbepack.filesystem import wdfs, TmpdirFilesystem
from elbepack.elbexml import ElbeXML, ValidationError, ValidationMode

from tempfile import NamedTemporaryFile

import sys
import time
import os
import datetime

import libvirt


def cmd_exists(x): return any(os.access(os.path.join(path, x), os.X_OK)
                              for path in os.environ["PATH"].split(os.pathsep))

# Create download directory with timestamp,
# if necessary


def ensure_outdir(wdfs, opt):
    if opt.outdir is None:
        opt.outdir = "elbe-build-%s" % (
                datetime.datetime.now().strftime("%Y%m%d-%H%M%S"))

    print("Saving generated Files to %s" % opt.outdir)


def ensure_initvm_defined():
    if self.initvm is None:
        sys.exit(20)


class InitVMError(Exception):
    def __init__(self, str):
        Exception.__init__(self, str)


class InitVMAction(object):
    actiondict = {}

    @classmethod
    def register(cls, action):
        cls.actiondict[action.tag] = action

    @classmethod
    def print_actions(cls):
        print("available subcommands are:", file=sys.stderr)
        for a in cls.actiondict:
            print("   %s" % a, file=sys.stderr)

    def __new__(cls, node):
        action = cls.actiondict[node]
        return object.__new__(action)

    def __init__(self, node, initvmNeeded=True):
        # The tag initvmNeeded is required in order to be able to run `elbe
        # initvm create`
        self.conn = libvirt.open("qemu:///session")
        try:
            self.initvm = self.conn.lookupByName('initvm')
        except libvirt.libvirtError:
            self.initvm = None
            if initvmNeeded:
                sys.exit(20)
        self.node = node

    def initvm_state(self):
        return self.initvm.info()[0]


class StartAction(InitVMAction):

    tag = 'start'

    def __init__(self, node):
        InitVMAction.__init__(self, node)

    def execute(self, initvmdir, opt, args):
        if self.initvm_state() == 1:
            print('Initvm already running.')
            sys.exit(20)
        elif self.initvm_state() == 5:
            # Domain is shut off. Let's start it!
            self.initvm.create()
            # Wait five seconds for the initvm to boot
            # TODO: Instead of waiting for five seconds
            # check whether SOAP server is reachable.
            for i in range(1, 5):
                sys.stdout.write("*")
                sys.stdout.flush()
                time.sleep(1)
            print("*")


InitVMAction.register(StartAction)


class EnsureAction(InitVMAction):

    tag = 'ensure'

    def __init__(self, node):
        InitVMAction.__init__(self, node)

    def execute(self, initvmdir, opt, args):
        if self.initvm_state() == 5:
            system('%s initvm start' % elbe_exe)
        elif self.initvm_state() == 1:
            pass
        else:
            print("Elbe initvm in bad state.")
            sys.exit(20)


InitVMAction.register(EnsureAction)


class StopAction(InitVMAction):

    tag = 'stop'

    def __init__(self, node):
        InitVMAction.__init__(self, node)

    def execute(self, initvmdir, opt, args):
        if self.initvm_state() != 1:
            print('Initvm is not running.')
            sys.exit(20)
        else:
            # Shutdown initvm
            self.initvm.shutdown()
            while(True):
                sys.stdout.write("*")
                sys.stdout.flush()
                if self.initvm_state() == 5:
                    print("\nInitvm shut off.")
                    break
                time.sleep(1)


InitVMAction.register(StopAction)


class AttachAction(InitVMAction):

    tag = 'attach'

    def __init__(self, node):
        InitVMAction.__init__(self, node)

    def execute(self, initvmdir, opt, args):
        if self.initvm_state() != 1:
            print('Error: Initvm not running properly.')
            sys.exit(20)

        print('Attaching to initvm console.')
        system('virsh console initvm')


InitVMAction.register(AttachAction)


class StartBuildAction(InitVMAction):

    tag = 'start_build'

    def __init__(self, node):
        InitVMAction.__init__(self, node)

    def execute(self, initvmdir, opt, args):
        try:
            have_session = os.system(
                "tmux has-session -t ElbeInitVMSession >/dev/null 2>&1")
        except CommandError as e:
            print("tmux exec failed, tmux version 1.9 or higher is required")
            sys.exit(20)
        if have_session != 256:
            print("ElbeInitVMSession already exists in tmux.", file=sys.stderr)
            print(
                "Try 'elbe initvm attach' to attach to the session.",
                file=sys.stderr)
            sys.exit(20)

        system('TMUX= tmux new-session -d -s ElbeInitVMSession -n initvm '
               '"cd \"%s\"; make"' % initvmdir)


InitVMAction.register(StartBuildAction)


class CreateAction(InitVMAction):

    tag = 'create'

    def __init__(self, node):
        InitVMAction.__init__(self, node, initvmNeeded=False)

    def execute(self, initvmdir, opt, args):
        if self.initvm is not None:
            print("Initvm already defined.\n")
            print("If you want to build in your old initvm, "
                  "use `elbe initvm submit <xml>`.")
            print("If you want to remove your old initvm from libvirt "
                  "run `virsh undefine initvm`.\n")
            print("Note:")
            print("\t1) You can reimport your old initvm via "
                  "`virsh define <file>`")
            print("\t   where <file> is the corresponding libvirt.xml")
            print("\t2) virsh undefine does not delete the image "
                  "of your old initvm.")
            sys.exit(20)

        # Init cdrom to None, if we detect it, we set it
        cdrom = None

        if len(args) == 1:
            if args[0].endswith('.xml'):
                # We have an xml file, use that for elbe init
                xmlfile = args[0]
                try:
                    xml = etree(xmlfile)
                except ValidationError as e:
                    print("XML file is inavlid: %s" % str(e))
                # Use default XML if no initvm was specified
                if not xml.has("initvm"):
                    xmlfile = os.path.join(
                        elbepack.__path__[0], "init/default-init.xml")

            elif args[0].endswith('.iso'):
                # We have an iso image, extract xml from there.
                tmp = TmpdirFilesystem()
                os.system('7z x -o%s "%s" source.xml' % (tmp.path, args[0]))

                print('', file=sys.stderr)

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
                print(
                    "Image was generated using Elbe Version %s" %
                    exml.get_elbe_version())

                os.system(
                    '7z x -o%s "%s" elbe-keyring.gpg' %
                    ('/tmp', args[0]))

                if tmp.isfile('elbe-keyring.gpg'):
                    print("Iso image contains a elbe-kerying")

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

            if cdrom:
                system('%s init %s --directory "%s" --cdrom "%s" "%s"' %
                       (elbe_exe, init_opts, initvmdir, cdrom, xmlfile))
            else:
                system(
                    '%s init %s --directory "%s" "%s"' %
                    (elbe_exe, init_opts, initvmdir, xmlfile))

        except CommandError:
            print("'elbe init' Failed", file=sys.stderr)
            print("Giving up", file=sys.stderr)
            sys.exit(20)

        # Register initvm in libvirt
        # TODO: Extended vm name support? Currently, only one initvm with the
        # name `initvm` is allowed. But perhaps it is a good idea to leave it
        # that way because otherwise the user may be tempted to start more than
        # one elbe-initvm which is not possible in the current network
        # configuration (user networking with portforwarding).

        # Read xml file
        with open(os.path.join(initvmdir, 'libvirt.xml')) as f:
            xml = f.read()

        try:
            self.conn.defineXML(xml)
        except CommandError:
            print('Registering initvm in libvirt failed', file=sys.stderr)
            print('Try `virsh undefine initvm` to delete existing initvm',
                  file=sys.stderr)
            sys.exit(20)

        # Build initvm
        try:
            system('cd "%s"; make' % (initvmdir))
        except CommandError:
            print("Building the initvm Failed", file=sys.stderr)
            print("Giving up", file=sys.stderr)
            sys.exit(20)

        try:
            system('%s initvm start' % elbe_exe)
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
                    x = ElbeXML(args[0])
                except ValidationError as e:
                    print("XML file is inavlid: %s" % str(e))
                    sys.exit(20)
                if not x.has('project'):
                    print("elbe initvm ready: use 'elbe initvm submit "
                          "myproject.xml' to build a project")
                    sys.exit(0)

                ret, prjdir, err = command_out_stderr(
                    '%s control create_project' % (elbe_exe))
                xmlfile = args[0]
            elif cdrom is not None:
                ret, prjdir, err = command_out_stderr(
                    '%s control create_project' % (elbe_exe))
                xmlfile = tmp.fname('source.xml')
            else:
                ret, prjdir, err = command_out_stderr(
                    '%s control create_project' % (elbe_exe))

            if ret != 0:
                print("elbe control create_project failed.", file=sys.stderr)
                print(err, file=sys.stderr)
                print("Giving up", file=sys.stderr)
                sys.exit(20)

            prjdir = prjdir.strip()

            cmd = '%s control set_xml %s %s' % (elbe_exe, prjdir, xmlfile)
            ret, msg, err = command_out_stderr(cmd)
            if ret != 0:
                print("elbe control set_xml failed.", file=sys.stderr)
                print(err, file=sys.stderr)
                print("Giving up", file=sys.stderr)
                sys.exit(20)

            if opt.writeproject:
                with open(opt.writeproject, "w") as wpf:
                    wpf.write(prjdir)

            if cdrom is not None:
                print("Uploading CDROM. This might take a while")
                try:
                    system(
                        '%s control set_cdrom "%s" "%s"' %
                        (elbe_exe, prjdir, cdrom))
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
                system(
                    '%s control build "%s" %s' %
                    (elbe_exe, prjdir, build_opts))
            except CommandError:
                print("elbe control build Failed", file=sys.stderr)
                print("Giving up", file=sys.stderr)
                sys.exit(20)

            print("Build started, waiting till it finishes")

            try:
                system('%s control wait_busy "%s"' % (elbe_exe, prjdir))
            except CommandError:
                print("elbe control wait_busy Failed", file=sys.stderr)
                print("Giving up", file=sys.stderr)
                sys.exit(20)

            print("")
            print("Build finished !")
            print("")
            try:
                system(
                    '%s control dump_file "%s" validation.txt' %
                    (elbe_exe, prjdir))
            except CommandError:
                print(
                    "Project failed to generate validation.txt",
                    file=sys.stderr)
                print("Getting log.txt", file=sys.stderr)
                try:
                    system(
                        '%s control dump_file "%s" log.txt' %
                        (elbe_exe, prjdir))
                except CommandError:

                    print("Failed to dump log.txt", file=sys.stderr)
                    print("Giving up", file=sys.stderr)
                sys.exit(20)

            if opt.skip_download:
                print("")
                print("Listing available files:")
                print("")
                try:
                    system('%s control get_files "%s"' % (elbe_exe, prjdir))
                except CommandError:
                    print("elbe control Failed", file=sys.stderr)
                    print("Giving up", file=sys.stderr)
                    sys.exit(20)

                print("")
                print(
                    'Get Files with: elbe control get_file "%s" <filename>' %
                    prjdir)
            else:
                print("")
                print("Getting generated Files")
                print("")

                ensure_outdir(wdfs, opt)

                try:
                    system('%s control get_files --output "%s" "%s"' % (
                        elbe_exe, opt.outdir, prjdir))
                except CommandError:
                    print("elbe control get_files Failed", file=sys.stderr)
                    print("Giving up", file=sys.stderr)
                    sys.exit(20)

                if not opt.keep_files:
                    try:
                        system('%s control del_project "%s"' % (
                            elbe_exe, prjdir))
                    except CommandError:
                        print("remove project from initvm failed",
                              file=sys.stderr)
                        sys.exit(20)


InitVMAction.register(CreateAction)


class SubmitAction(InitVMAction):

    tag = 'submit'

    def __init__(self, node):
        InitVMAction.__init__(self, node)

    def execute(self, initvmdir, opt, args):
        try:
            system('%s initvm ensure' % elbe_exe)
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
                url_validation = ''
            elif args[0].endswith('.iso'):
                # We have an iso image, extract xml from there.
                tmp = TmpdirFilesystem()
                os.system('7z x -o%s "%s" source.xml' % (tmp.path, args[0]))

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
                print(
                    "Image was generated using Elbe Version %s" %
                    exml.get_elbe_version())

                xmlfile = tmp.fname('source.xml')
                url_validation = '--skip-urlcheck'
                cdrom = args[0]
            else:
                print(
                    "Unknown file ending (use either xml or iso)",
                    file=sys.stderr)
                sys.exit(20)

            outxml = NamedTemporaryFile(prefix='elbe', suffix='xml')
            cmd = '%s preprocess -o %s %s' % (elbe_exe, outxml.name, xmlfile)
            ret, msg, err = command_out_stderr(cmd)
            if ret != 0:
                print("elbe preprocess failed.", file=sys.stderr)
                print(err, file=sys.stderr)
                print("Giving up", file=sys.stderr)
                sys.exit(20)
            xmlfile = outxml.name

            ret, prjdir, err = command_out_stderr(
                '%s control create_project' % (elbe_exe))
            if ret != 0:
                print("elbe control create_project failed.", file=sys.stderr)
                print(err, file=sys.stderr)
                print("Giving up", file=sys.stderr)
                sys.exit(20)

            prjdir = prjdir.strip()

            cmd = '%s control set_xml %s %s' % (elbe_exe, prjdir, xmlfile)
            ret, msg, err = command_out_stderr(cmd)
            if ret != 0:
                print("elbe control set_xml failed2", file=sys.stderr)
                print(err, file=sys.stderr)
                print("Giving up", file=sys.stderr)
                sys.exit(20)

            if opt.writeproject:
                with open(opt.writeproject, "w") as wpf:
                    wpf.write(prjdir)

            if cdrom is not None:
                print("Uploading CDROM. This might take a while")
                try:
                    system(
                        '%s control set_cdrom "%s" "%s"' %
                        (elbe_exe, prjdir, cdrom))
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
                system(
                    '%s control build "%s" %s' %
                    (elbe_exe, prjdir, build_opts))
            except CommandError:
                print("elbe control build Failed", file=sys.stderr)
                print("Giving up", file=sys.stderr)
                sys.exit(20)

            print("Build started, waiting till it finishes")

            try:
                system('%s control wait_busy "%s"' % (elbe_exe, prjdir))
            except CommandError:
                print("elbe control wait_busy Failed", file=sys.stderr)
                print("Giving up", file=sys.stderr)
                sys.exit(20)

            print("")
            print("Build finished !")
            print("")
            try:
                system(
                    '%s control dump_file "%s" validation.txt' %
                    (elbe_exe, prjdir))
            except CommandError:
                print(
                    "Project failed to generate validation.txt",
                    file=sys.stderr)
                print("Getting log.txt", file=sys.stderr)
                try:
                    system(
                        '%s control dump_file "%s" log.txt' %
                        (elbe_exe, prjdir))
                except CommandError:

                    print("Failed to dump log.txt", file=sys.stderr)
                    print("Giving up", file=sys.stderr)
                sys.exit(20)

            if opt.skip_download:
                print("")
                print("Listing available files:")
                print("")
                try:
                    system('%s control get_files "%s"' % (elbe_exe, prjdir))
                except CommandError:
                    print("elbe control get_files Failed", file=sys.stderr)
                    print("Giving up", file=sys.stderr)
                    sys.exit(20)

                print("")
                print(
                    'Get Files with: elbe control get_file "%s" <filename>' %
                    prjdir)
            else:
                print("")
                print("Getting generated Files")
                print("")

                ensure_outdir(wdfs, opt)

                try:
                    system('%s control get_files --output "%s" "%s"' % (
                        elbe_exe, opt.outdir, prjdir))
                except CommandError:
                    print("elbe control get_files Failed", file=sys.stderr)
                    print("Giving up", file=sys.stderr)
                    sys.exit(20)

                if not opt.keep_files:
                    try:
                        system('%s control del_project "%s"' % (
                            elbe_exe, prjdir))
                    except CommandError:
                        print("remove project from initvm failed",
                              file=sys.stderr)
                        sys.exit(20)


InitVMAction.register(SubmitAction)
