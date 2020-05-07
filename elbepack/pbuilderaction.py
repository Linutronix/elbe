# ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (c) 2015-2016 Torben Hohn <torben.hohn@linutronix.de>
# Copyright (c) 2016-2017 Manuel Traut <manut@linutronix.de>
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import print_function

import sys
import os

from elbepack.directories import elbe_exe
from elbepack.shellhelper import CommandError, system, command_out_stderr
from elbepack.filesystem import TmpdirFilesystem
from elbepack.xmlpreprocess import PreprocessWrapper


def cmd_exists(x):
    return any(os.access(os.path.join(path, x), os.X_OK)
               for path in os.environ["PATH"].split(os.pathsep))

# Create download directory with timestamp,
# if necessary


def ensure_outdir(opt):
    if opt.outdir is None:
        opt.outdir = ".."

    print("Saving generated Files to %s" % opt.outdir)


class PBuilderError(Exception):
    def __init__(self, msg):
        Exception.__init__(self, msg)


class PBuilderAction(object):
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

    def __init__(self, node):
        self.node = node

    def execute(self, _opt, _args):
        raise NotImplementedError('execute() not implemented')


class CreateAction(PBuilderAction):

    tag = 'create'

    def __init__(self, node):
        PBuilderAction.__init__(self, node)

    def execute(self, opt, _args):
        crossopt = ""
        if opt.cross:
            crossopt = "--cross"

        if opt.xmlfile:
            try:
                with PreprocessWrapper(opt.xmlfile, opt) as ppw:
                    ret, prjdir, err = command_out_stderr(
                        '%s control create_project' % (elbe_exe))
                    if ret != 0:
                        print("elbe control create_project failed.",
                              file=sys.stderr)
                        print(err, file=sys.stderr)
                        print("Giving up", file=sys.stderr)
                        sys.exit(20)

                    prjdir = prjdir.strip()
                    ret, _, err = command_out_stderr(
                        '%s control set_xml "%s" "%s"' %
                        (elbe_exe, prjdir, ppw.preproc))

                    if ret != 0:
                        print("elbe control set_xml failed.", file=sys.stderr)
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
                wpf = open(opt.writeproject, "w")
                wpf.write(prjdir)
                wpf.close()

        elif opt.project:
            prjdir = opt.project
        else:
            print("you need to specify --project option", file=sys.stderr)
            sys.exit(20)

        print("Creating pbuilder")

        try:
            system('%s control build_pbuilder "%s" "%s"' % (elbe_exe,
                                                            prjdir,
                                                            crossopt))
        except CommandError:
            print("elbe control build_pbuilder Failed", file=sys.stderr)
            print("Giving up", file=sys.stderr)
            sys.exit(20)

        try:
            system('%s control wait_busy "%s"' % (elbe_exe, prjdir))
        except CommandError:
            print("elbe control wait_busy Failed", file=sys.stderr)
            print("Giving up", file=sys.stderr)
            sys.exit(20)

        print("")
        print("Building Pbuilder finished !")
        print("")


PBuilderAction.register(CreateAction)


class UpdateAction(PBuilderAction):

    tag = 'update'

    def __init__(self, node):
        PBuilderAction.__init__(self, node)

    def execute(self, opt, _args):

        if not opt.project:
            print("you need to specify --project option", file=sys.stderr)
            sys.exit(20)

        prjdir = opt.project

        print("Updating pbuilder")

        try:
            system('%s control update_pbuilder "%s"' % (elbe_exe, prjdir))
        except CommandError:
            print("elbe control update_pbuilder Failed", file=sys.stderr)
            print("Giving up", file=sys.stderr)
            sys.exit(20)

        print("")
        print("Updating Pbuilder finished !")
        print("")


PBuilderAction.register(CreateAction)


class BuildAction(PBuilderAction):

    tag = 'build'

    def __init__(self, node):
        PBuilderAction.__init__(self, node)

    def execute(self, opt, _args):

        # pylint: disable=too-many-statements
        # pylint: disable=too-many-branches

        crossopt = ""
        if opt.cross:
            crossopt = "--cross"
        tmp = TmpdirFilesystem()

        if opt.xmlfile:
            ret, prjdir, err = command_out_stderr(
                '%s control create_project --retries 60 "%s"' %
                (elbe_exe, opt.xmlfile))
            if ret != 0:
                print("elbe control create_project failed.", file=sys.stderr)
                print(err, file=sys.stderr)
                print("Giving up", file=sys.stderr)
                sys.exit(20)

            prjdir = prjdir.strip()

            try:
                system('%s control build_pbuilder "%s"' % (elbe_exe, prjdir))
            except CommandError:
                print("elbe control build_pbuilder Failed", file=sys.stderr)
                print("Giving up", file=sys.stderr)
                sys.exit(20)

            try:
                system('%s control wait_busy "%s"' % (elbe_exe, prjdir))
            except CommandError:
                print("elbe control wait_busy Failed", file=sys.stderr)
                print("Giving up", file=sys.stderr)
                sys.exit(20)

            print("")
            print("Building Pbuilder finished !")
            print("")
        elif opt.project:
            prjdir = opt.project
            system('%s control rm_log %s' % (elbe_exe, prjdir))
        else:
            print(
                "you need to specify --project or --xmlfile option",
                file=sys.stderr)
            sys.exit(20)

        print("")
        print("Packing Source into tmp archive")
        print("")
        try:
            system('tar cfz "%s" .' % (tmp.fname("pdebuild.tar.gz")))
        except CommandError:
            print("tar Failed", file=sys.stderr)
            print("Giving up", file=sys.stderr)
            sys.exit(20)

        for of in opt.origfile:
            print("")
            print("Pushing orig file '%s' into pbuilder" % of)
            print("")
            try:
                system(
                    '%s control set_orig "%s" "%s"' %
                    (elbe_exe, prjdir, of))
            except CommandError:
                print("elbe control set_orig Failed", file=sys.stderr)
                print("Giving up", file=sys.stderr)
                sys.exit(20)

        print("")
        print("Pushing source into pbuilder")
        print("")

        try:
            system('%s control set_pdebuild --cpuset "%d" --profile "%s" "%s" '
                   '"%s" "%s"' %
                   (elbe_exe, opt.cpuset, opt.profile, crossopt,
                    prjdir, tmp.fname("pdebuild.tar.gz")))
        except CommandError:
            print("elbe control set_pdebuild Failed", file=sys.stderr)
            print("Giving up", file=sys.stderr)
            sys.exit(20)
        try:
            system('%s control wait_busy "%s"' % (elbe_exe, prjdir))
        except CommandError:
            print("elbe control wait_busy Failed", file=sys.stderr)
            print("Giving up", file=sys.stderr)
            sys.exit(20)
        print("")
        print("Pdebuild finished !")
        print("")

        if opt.skip_download:
            print("")
            print("Listing available files:")
            print("")
            try:
                system(
                    '%s control --pbuilder-only get_files "%s"' %
                    (elbe_exe, prjdir))
            except CommandError:
                print("elbe control get_files Failed", file=sys.stderr)
                print("", file=sys.stderr)
                print("dumping logfile", file=sys.stderr)

                try:
                    system('%s control dump_file "%s" log.txt' % (
                        elbe_exe, prjdir))
                except CommandError:
                    print("elbe control dump_file Failed", file=sys.stderr)
                    print("", file=sys.stderr)
                    print("Giving up", file=sys.stderr)

                sys.exit(20)

            print("")
            print(
                "Get Files with: 'elbe control get_file %s <filename>'" %
                prjdir)
        else:
            print("")
            print("Getting generated Files")
            print("")

            ensure_outdir(opt)

            try:
                system(
                    '%s control --pbuilder-only get_files --output "%s" "%s"' %
                    (elbe_exe, opt.outdir, prjdir))
            except CommandError:
                print("elbe control get_files Failed", file=sys.stderr)
                print("", file=sys.stderr)
                print("dumping logfile", file=sys.stderr)

                try:
                    system('%s control dump_file "%s" log.txt' % (
                        elbe_exe, prjdir))
                except CommandError:
                    print("elbe control dump_file Failed", file=sys.stderr)
                    print("", file=sys.stderr)
                    print("Giving up", file=sys.stderr)

                sys.exit(20)


PBuilderAction.register(BuildAction)
