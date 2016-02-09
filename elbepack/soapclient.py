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

from __future__ import print_function

import binascii
from suds.client import Client
from urllib2 import URLError
import socket
import time
import sys
import os

from elbepack.filesystem import Filesystem
from elbepack.elbexml import ElbeXML

def set_suds_debug(debug):
    import logging
    if debug:
        logging.basicConfig(level=logging.INFO)
        logging.getLogger('suds.client').setLevel(logging.DEBUG)
        logging.getLogger('suds.transport').setLevel(logging.DEBUG)
        logging.getLogger('suds.xsd.schema').setLevel(logging.DEBUG)
        logging.getLogger('suds.wsdl').setLevel(logging.DEBUG)
        logging.getLogger('suds.resolver').setLevel(logging.DEBUG)
        logging.getLogger('suds.umx.typed').setLevel(logging.DEBUG)
    else:
        logging.basicConfig(level=logging.CRITICAL)
        logging.getLogger('suds.umx.typed').setLevel(logging.ERROR)
        logging.getLogger('suds.client').setLevel(logging.CRITICAL)

class ElbeSoapClient(object):
    def __init__(self, host, port, user, passwd, retries = 10, debug=False):

        # Mess with suds logging, for debug, or squelch warnings
        set_suds_debug (debug)

        # Attributes
        self.wsdl = "http://" + host + ":" + str(port) + "/soap/?wsdl"
        self.control = None
        self.retries = 0

        # Loop and try to connect
        while self.control is None:
            self.retries += 1
            try:
                self.control = Client (self.wsdl)
            except socket.error as e:
                if self.retries > retries:
                    raise e
                time.sleep(1)
            except URLError as e:
                if self.retries > retries:
                    raise e
                time.sleep(1)

        # Make sure, that client.service still maps
        # to the service object.
        self.service = self.control.service

        # We have a Connection, now login
        self.service.login(user,passwd)

    def download_file (self, builddir, filename, dst_fname):
        fp = file (dst_fname, "w")
        part = 0
        while True:
            ret = self.service.get_file (builddir, filename, part)
            if ret == "FileNotFound":
                print (ret, file=sys.stderr)
                sys.exit(20)
            if ret == "EndOfFile":
                fp.close ()
                return

            fp.write (binascii.a2b_base64 (ret))
            part = part + 1

class ClientAction(object):
    actiondict = {}
    @classmethod
    def register(cls, action):
        cls.actiondict[action.tag] = action
    @classmethod
    def print_actions(cls):
        print ('available subcommands are:', file=sys.stderr)
        for a in cls.actiondict:
            print ('   ' + a, file=sys.stderr)
    def __new__(cls, node):
        action = cls.actiondict[node]
        return object.__new__(action, node)
    def __init__(self, node):
        self.node = node

class ListProjectsAction(ClientAction):

    tag = 'list_projects'

    def __init__(self, node):
        ClientAction.__init__(self, node)

    def execute(self, client, opt, args):
        projects = client.service.list_projects ()

        try:
            for p in projects.SoapProject:
                print (p.builddir + '\t' + p.name + '\t' + p.version + '\t' + p.status + '\t' + str(p.edit))
        except AttributeError:
            print ('No projects configured in initvm')

ClientAction.register(ListProjectsAction)

class ListUsersAction(ClientAction):

    tag = 'list_users'

    def __init__(self, node):
        ClientAction.__init__(self, node)

    def execute(self, client, opt, args):
        users = client.service.list_users (client)

        for u in users.string:
            print (u)

ClientAction.register(ListUsersAction)

class CreateProjectAction(ClientAction):

    tag = 'create_project'

    def __init__(self, node):
        ClientAction.__init__(self, node)

    def execute(self, client, opt, args):
        if len (args) != 1:
            print ("usage: elbe control create_project <xmlfile>", file=sys.stderr)
            sys.exit(20)

        filename = args[0]

        if not os.path.isfile (filename):
            print ("%s doesn't exist" % filename, file=sys.stderr)
            sys.exit (20)

        x = ElbeXML (filename, skip_validate=True, skip_urlcheck=True)
        if not x.has ('target'):
          print ("<target> is missing, this file can't be built in an initvm",
                  file=sys.stderr)
          sys.exit (20)

        with file (filename, "r") as fp:
            xml_base64 = binascii.b2a_base64(fp.read ())
            print (client.service.create_project ( xml_base64 ))

ClientAction.register(CreateProjectAction)

class ResetProjectAction(ClientAction):

    tag = 'reset_project'

    def __init__(self, node):
        ClientAction.__init__(self, node)

    def execute(self, client, opt, args):
        if len (args) != 1:
            print ("usage: elbe control reset_project <project_dir>", file=sys.stderr)
            sys.exit(20)

        builddir = args[0]
        client.service.reset_project (builddir)

ClientAction.register(ResetProjectAction)


class DeleteProjectAction(ClientAction):

    tag = 'del_project'

    def __init__(self, node):
        ClientAction.__init__(self, node)

    def execute(self, client, opt, args):
        if len (args) != 1:
            print ("usage: elbe control del_project <project_dir>", file=sys.stderr)
            sys.exit(20)

        builddir = args[0]
        client.service.del_project (builddir)

ClientAction.register(DeleteProjectAction)

class SetXmlAction(ClientAction):

    tag = 'set_xml'

    def __init__(self, node):
        ClientAction.__init__(self, node)

    def execute(self, client, opt, args):
        if len (args) != 2:
            print ("usage: elbe control set_xml <project_dir> <xml>", file=sys.stderr)
            sys.exit(20)

        builddir = args[0]
        filename = args[1]
        with file (filename, "r") as fp:
            xml_base64 = binascii.b2a_base64(fp.read ())
            client.service.set_xml (builddir, xml_base64)

ClientAction.register(SetXmlAction)


class BuildAction(ClientAction):

    tag = 'build'

    def __init__(self, node):
        ClientAction.__init__(self, node)

    def execute(self, client, opt, args):
        if len (args) != 1:
            print ("usage: elbe control build <project_dir>", file=sys.stderr)
            sys.exit(20)

        builddir = args[0]
        client.service.build (builddir, opt.build_bin, opt.build_sources)

ClientAction.register(BuildAction)


class BuildSysrootAction(ClientAction):

    tag = 'build_sysroot'

    def __init__(self, node):
        ClientAction.__init__(self, node)

    def execute(self, client, opt, args):
        if len (args) != 1:
            print ("usage: elbe control build-sysroot <project_dir>", file=sys.stderr)
            sys.exit(20)

        builddir = args[0]
        client.service.build_sysroot (builddir)

ClientAction.register(BuildSysrootAction)


class GetFileAction(ClientAction):

    tag = 'get_file'

    def __init__(self, node):
        ClientAction.__init__(self, node)

    def execute(self, client, opt, args):
        if len (args) != 2:
            print ("usage: elbe control get_file <project_dir> <file>", file=sys.stderr)
            sys.exit(20)

        builddir = args[0]
        filename = args[1]
        dst_fname = filename

        if opt.output:
            fs = Filesystem ('/')
            dst = os.path.abspath (opt.output)
            fs.mkdir_p (dst)
            dst_fname = str (os.path.join (dst, filename))

        client.download_file (builddir, filename, dst_fname)
        print (dst_fname + " saved", file=sys.stderr)

ClientAction.register(GetFileAction)

class GetBuildChrootAction(ClientAction):

    tag = 'get_build_chroot_tarball'

    def __init__(self, node):
        ClientAction.__init__(self, node)

    def execute(self, client, opt, args):
        if len (args) != 1:
            print ("usage: elbe control get_build_chroot_tarball <project_dir>", file=sys.stderr)
            sys.exit(20)

        builddir = args[0]
        dst_fname = "build_chroot.tar.xz"

        if opt.output:
            fs = Filesystem ('/')
            dst = os.path.abspath (opt.output)
            fs.mkdir_p (dst)
            dst_fname = str (os.path.join (dst, filename))

        with file (dst_fname, "w") as fp:
            part = 0
            while True:
                ret = client.service.get_build_chroot_tarball (builddir, part)
                if ret == "EndOfFile":
                    break

                fp.write (binascii.a2b_base64 (ret))
                part = part + 1
        print (dst_fname + " saved", file=sys.stderr)

ClientAction.register(GetBuildChrootAction)

class DumpFileAction(ClientAction):

    tag = 'dump_file'

    def __init__(self, node):
        ClientAction.__init__(self, node)

    def execute(self, client, opt, args):
        if len (args) != 2:
            print ("usage: elbe control dump_file <project_dir> <file>", file=sys.stderr)
            sys.exit(20)

        builddir = args[0]
        filename = args[1]

        part = 0
        while True:
            ret = client.service.get_file (builddir, filename, part)
            if ret == "FileNotFound":
                print (ret, file=sys.stderr)
                sys.exit(20)
            if ret == "EndOfFile":
                return

            sys.stdout.write (binascii.a2b_base64 (ret))
            part = part + 1

ClientAction.register(DumpFileAction)

class GetFilesAction(ClientAction):

    tag = 'get_files'

    def __init__(self, node):
        ClientAction.__init__(self, node)

    def execute(self, client, opt, args):
        if len (args) != 1:
            print ("usage: elbe control get_files <project_dir>", file=sys.stderr)
            sys.exit(20)

        builddir = args[0]
        files = client.service.get_files (builddir)

        nfiles = 0

        for f in files.SoapFile:
            if opt.pbuilder_only and not f.name.startswith ('pbuilder'):
                continue

            nfiles += 1
            if f.description:
                print ("%s \t(%s)" % (f.name, f.description))
            else:
                print ("%s" % (f.name))

            if opt.output:
                fs = Filesystem ('/')
                dst = os.path.abspath (opt.output)
                fs.mkdir_p (dst)
                dst_fname = str (os.path.join (dst, os.path.basename (f.name)))
                client.download_file (builddir, f.name, dst_fname)

        if nfiles == 0:
            sys.exit (10)

ClientAction.register(GetFilesAction)

class WaitProjectBusyAction(ClientAction):

    tag = 'wait_busy'

    def __init__(self, node):
        ClientAction.__init__(self, node)

    def execute(self, client, opt, args):
        if len (args) != 1:
            print ("usage: elbe control wait_busy <project_dir>", file=sys.stderr)
            sys.exit(20)

        builddir = args[0]

        while True:
            busy = client.service.get_project_busy (builddir)
            if not busy:
                break
            else:
                localtime = time.asctime(time.localtime(time.time()))
                print (localtime + "-- project still busy, waiting")
                time.sleep(5)

ClientAction.register(WaitProjectBusyAction)

class SetCdromAction(ClientAction):

    tag = 'set_cdrom'

    def __init__(self, node):
        ClientAction.__init__(self, node)

    def execute(self, client, opt, args):
        size = 5 * 1024 * 1024

        if len (args) != 2:
            print ("usage: elbe control set_cdrom <project_dir> <cdrom file>", file=sys.stderr)
            sys.exit(20)

        builddir = args[0]
        filename = args[1]

        fp = file (filename, "r")
        client.service.start_cdrom (builddir)
        while True:
            bindata = fp.read (size)
            client.service.append_cdrom (builddir, binascii.b2a_base64 (bindata))
            if len (bindata) != size:
                break

        client.service.finish_cdrom (builddir)

ClientAction.register(SetCdromAction)

class ShutdownInitvmAction(ClientAction):

    tag = 'shutdown_initvm'

    def __init__(self, node):
        ClientAction.__init__(self, node)

    def execute(self, client, opt, args):
        if len (args) != 0:
            print ("usage: elbe control shutdown_initvm", file=sys.stderr)
            sys.exit(20)

        client.service.shutdown_initvm ()

ClientAction.register(ShutdownInitvmAction)

class SetPdebuilderAction(ClientAction):

    tag = 'set_pdebuild'

    def __init__(self, node):
        ClientAction.__init__(self, node)

    def execute(self, client, opt, args):
        size = 5 * 1024 * 1024

        if len (args) != 2:
            print ("usage: elbe control set_pdebuild <project_dir> <pdebuild file>", file=sys.stderr)
            sys.exit(20)

        builddir = args[0]
        filename = args[1]

        fp = file (filename, "r")
        client.service.start_pdebuild (builddir)
        while True:
            bindata = fp.read (size)
            client.service.append_pdebuild (builddir, binascii.b2a_base64 (bindata))
            if len (bindata) != size:
                break

        client.service.finish_pdebuild (builddir)

ClientAction.register(SetPdebuilderAction)

class BuildPbuilderAction(ClientAction):

    tag = 'build_pbuilder'

    def __init__(self, node):
        ClientAction.__init__(self, node)

    def execute(self, client, opt, args):
        if len (args) != 1:
            print ("usage: elbe control build_pbuilder <project_dir>", file=sys.stderr)
            sys.exit(20)

        builddir = args[0]
        client.service.build_pbuilder (builddir)

ClientAction.register(BuildPbuilderAction)

