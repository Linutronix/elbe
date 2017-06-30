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
from httplib import BadStatusLine
import socket
import time
import sys
import os
import fnmatch

from datetime import datetime
import deb822                     # package for dealing with Debian related data

from elbepack.filesystem import Filesystem
from elbepack.elbexml import ElbeXML, ValidationMode

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
            except BadStatusLine as e:
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
            try:
                ret = self.service.get_file (builddir, filename, part)
            except BadStatusLine as e:
                retry = retry - 1
                if not retry:
                    fp.close ()
                    print ("file transfer failed", file=sys.stderr)
                    sys.exit(20)

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
        return object.__new__(action)
    def __init__(self, node):
        self.node = node

class RemoveLogAction(ClientAction):

    tag = 'rm_log'

    def __init__(self, node):
        ClientAction.__init__(self, node)

    def execute(self, client, opt, args):
        if len (args) != 1:
            print ("usage: elbe control rm_log <project_dir>", file=sys.stderr)
            sys.exit(20)

        builddir = args[0]
        client.service.rm_log (builddir)


ClientAction.register(RemoveLogAction)

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
        users = client.service.list_users ()

        for u in users.string:
            print (u)

ClientAction.register(ListUsersAction)

class CreateProjectAction(ClientAction):

    tag = 'create_project'

    def __init__(self, node):
        ClientAction.__init__(self, node)

    def execute(self, client, opt, args):

        uuid = client.service.new_project ()
        print (uuid)

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

        try:
            x = ElbeXML (filename, skip_validate=True, url_validation=ValidationMode.NO_CHECK)
        except IOError as e:
            print ("%s is not a valid elbe xml file" % filename)
            sys.exit (20)

        if not x.has ('target'):
          print ("<target> is missing, this file can't be built in an initvm",
                  file=sys.stderr)
          sys.exit (20)

        size = 1024 * 1024
        part = 0
        with file (filename, "r") as fp:
            while (True):
                xml_base64 = binascii.b2a_base64(fp.read (size))
                # finish upload
                if len (xml_base64) == 1:
                    part = client.service.upload_file (builddir,
                                                       "source.xml",
                                                       xml_base64,
                                                       -1)
                else:
                    part = client.service.upload_file (builddir,
                                                       "source.xml",
                                                       xml_base64,
                                                       part)
                if part == -1:
                    print ("project busy, upload not allowed")
                    return part
                if part == -2:
                    print ("upload of xml finished")
                    return 0


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
        client.service.build (builddir, opt.build_bin, opt.build_sources,
                opt.skip_pbuilder)

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

class BuildChrootAction(ClientAction):

    tag = 'build_chroot_tarball'

    def __init__(self, node):
        ClientAction.__init__(self, node)

    def execute(self, client, opt, args):
        if len (args) != 1:
            print ("usage: elbe control build_chroot_tarball <project_dir>", file=sys.stderr)
            sys.exit(20)

        builddir = args[0]

        client.service.build_chroot_tarball (builddir)

ClientAction.register(BuildChrootAction)

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

        for f in files[0]:
            if opt.pbuilder_only and not f.name.startswith ('pbuilder'):
                continue

            if opt.matches and not fnmatch.fnmatch(f.name, opt.matches):
                continue

            nfiles += 1
            try:
                print ("%s \t(%s)" % (f.name, f.description))
            except AttributeError:
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
        part = 1

        while True:
            busy = client.service.get_project_busy (builddir, part)
            if busy == 'FINISH':
                break
            else:
                # for some reasons lines containing e.g. ^H result in a None
                # object here. let's just skip those strange lines for the
                # moment
                if (busy):
                    log = busy.split('###')

                    if part != int(log[0]):
                        part = int(log[0])

                        localtime = time.asctime(time.localtime(time.time()))
                        try:
                            print (localtime + " -- " + log[1].replace('\n', ''))
                        except IndexError:
                            pass
                    else:
                        time.sleep(1)
                else:
                    print ("strange part: %d (skipped)" % part)
                    part = part+1

ClientAction.register(WaitProjectBusyAction)

class SetCdromAction(ClientAction):

    tag = 'set_cdrom'

    def __init__(self, node):
        ClientAction.__init__(self, node)

    def execute(self, client, opt, args):
        size = 1024 * 1024

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

class SetOrigAction(ClientAction):

    tag = 'set_orig'

    def __init__(self, node):
        ClientAction.__init__(self, node)

    def execute(self, client, opt, args):
        size =  1024 * 1024

        if len (args) != 2:
            print ("usage: elbe control set_orig <project_dir> <orig file>", file=sys.stderr)
            sys.exit(20)

        builddir = args[0]
        filename = args[1]

        fp = file (filename, "r")
        client.service.start_upload_orig (builddir, os.path.basename(filename))
        while True:
            bindata = fp.read (size)
            client.service.append_upload_orig (builddir, binascii.b2a_base64 (bindata))
            if len (bindata) != size:
                break

        client.service.finish_upload_orig (builddir)

ClientAction.register(SetOrigAction)

class ShutdownInitvmAction(ClientAction):

    tag = 'shutdown_initvm'

    def __init__(self, node):
        ClientAction.__init__(self, node)

    def execute(self, client, opt, args):
        if len (args) != 0:
            print ("usage: elbe control shutdown_initvm", file=sys.stderr)
            sys.exit(20)

        # if shutdown kills the daemon before it can answer the request
        try:
            client.service.shutdown_initvm ()
        except BadStatusLine:
            pass

ClientAction.register(ShutdownInitvmAction)

class SetPdebuilderAction(ClientAction):

    tag = 'set_pdebuild'

    def __init__(self, node):
        ClientAction.__init__(self, node)

    def execute(self, client, opt, args):
        size = 1024 * 1024

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


class RepoAction(ClientAction):
    repoactiondict = {}
    @classmethod
    def register(cls, action):
        cls.repoactiondict[action.tag] = action
    @classmethod
    def print_actions(cls):
        print ('available subcommands are:', file=sys.stderr)
        for a in cls.repoactiondict:
            print ('   ' + a, file=sys.stderr)
    def __new__(cls, node):
        action = cls.repoactiondict[node]
        return object.__new__(action)


class ListPackagesAction(RepoAction):

    tag = 'list_packages'

    def __init__(self, node):
        RepoAction.__init__(self, node)

    def execute(self, client, opt, args):
        if len (args) != 1:
            print ("usage: elbe prjrepo list_packages <project_dir>", file=sys.stderr)
            sys.exit(20)

        builddir = args[0]
        print(client.service.list_packages (builddir))

RepoAction.register(ListPackagesAction)


class DownloadAction(RepoAction):

    tag = 'download'

    def __init__(self, node):
        RepoAction.__init__(self, node)

    def execute(self, client, opt, args):
        if len (args) != 1:
            print ("usage: elbe prjrepo download <project_dir>", file=sys.stderr)
            sys.exit(20)

        builddir = args[0]
        filename = "repo.tar.gz"
        client.service.tar_prjrepo (builddir, filename)

        dst_fname = os.path.join(".", "elbe-projectrepo-" + datetime.now().strftime("%Y%m%d-%H%M%S") + ".tar.gz")

        client.download_file (builddir, filename, dst_fname)
        print (dst_fname + " saved", file=sys.stderr)

        client.service.rm (builddir, filename)
        print (filename + " deleted on initvm.")


RepoAction.register(DownloadAction)


class UploadPackageAction(RepoAction):

    tag = 'upload_pkg'

    def __init__(self, node):
        RepoAction.__init__(self, node)

    def upload_file(self, client, f, builddir):
        # Uploads file f into builddir in intivm
        size = 1024 * 1024
        part = 0
        with file (f, "r") as fp:
            while (True):
                xml_base64 = binascii.b2a_base64(fp.read (size))
                # finish upload
                if len (xml_base64) == 1:
                    part = client.service.upload_file (builddir,
                                                       f,
                                                       xml_base64,
                                                       -1)
                else:
                    part = client.service.upload_file (builddir,
                                                       f,
                                                       xml_base64,
                                                       part)
                if part == -1:
                    print ("project busy, upload not allowed")
                    return -1
                if part == -2:
                    print ("Upload of package finished.")
                    break

    def execute(self, client, opt, args):
        if len (args) != 2:
            print ("usage: elbe prjrepo upload_pkg <project_dir> <deb/dsc file>", file=sys.stderr)
            sys.exit(20)

        builddir = args[0]
        filename = args[1]

        print("\n--------------------------")
        print("Upload and Include Package")
        print("--------------------------")
        print("Check files...")

        # Check filetype
        if filename[-3:] not in ['dsc','deb']:
            print ("Error: Only .dsc and .deb files allowed to upload.")
        else:
            filetype = filename[-4:]

        files = [filename] # list of all files which will be uploaded

        # Parse .dsc-File and append neccessary source files to files
        if filetype == '.dsc':
            for f in deb822.Dsc(file(filename))['Files']:
                files.append(f['name'])

        # Check whether all files are available
        abort = False
        for f in files:
            if not os.path.isfile(f):
                print("File %s not found." % f)
                abort = True
        # Abort if one or more source files are missing
        if abort: sys.exit(20)

        print ("Start uploading file(s)...")
        for f in files:
            print("Upload %s..." % f)
            self.upload_file(client, f, builddir)

        print ("Including Package in initvm...")
        client.service.include_package(builddir, filename)


        print("Cleaning initvm builddir...")
        for f in files:
            client.service.rm (builddir, f)


RepoAction.register(UploadPackageAction)
