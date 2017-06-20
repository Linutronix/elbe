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

import os
import gpgme

from apt.package import FetchError
from shutil import rmtree
from io import BytesIO

from elbepack.repomanager import UpdateRepo
from elbepack.rpcaptcache import get_rpcaptcache
from elbepack.shellhelper import CommandError

class FinetuningAction(object):

    actiondict = {}

    @classmethod
    def register(cls, action):
        cls.actiondict[action.tag] = action

    def __new__(cls, node):
        action = cls.actiondict[node.tag]
        return object.__new__(action)

    def __init__(self, node):
        self.node = node


class RmAction(FinetuningAction):

    tag = 'rm'

    def __init__(self, node):
        FinetuningAction.__init__(self, node)

    def execute(self, log, buildenv, target):
        files = target.glob( self.node.et.text )

        if self.node.et.attrib.has_key ('exclude'):
            exclude = self.node.et.attrib['exclude'].split (' ')
        else:
            exclude = []

        for f in files:
            if os.path.basename (f) in exclude:
                continue

            log.do( "rm -rvf '%s'" % f )

FinetuningAction.register( RmAction )


class MkdirAction(FinetuningAction):

    tag = 'mkdir'

    def __init__(self, node):
        FinetuningAction.__init__(self, node)

    def execute(self, log, buildenv, target):
        log.do( "mkdir -p " + target.fname( self.node.et.text ) )

FinetuningAction.register( MkdirAction )

class MknodAction(FinetuningAction):

    tag = 'mknod'

    def __init__(self, node):
        FinetuningAction.__init__(self, node)

    def execute(self, log, buildenv, target):
        log.do( "mknod " + target.fname( self.node.et.text ) + " " + self.node.et.attrib['opts'] )

FinetuningAction.register( MknodAction )

class BuildenvMkdirAction(FinetuningAction):

    tag = 'buildenv_mkdir'

    def __init__(self, node):
        FinetuningAction.__init__(self, node)

    def execute(self, log, buildenv, target):
        log.do( "mkdir -p " + buildenv.rfs.fname( self.node.et.text ) )

FinetuningAction.register( BuildenvMkdirAction )


class CpAction(FinetuningAction):

    tag = 'cp'

    def __init__(self, node):
        FinetuningAction.__init__(self, node)

    def execute(self, log, buildenv, target):
        log.do( "cp -av " + target.fname( self.node.et.attrib['path'] ) + " " + target.fname( self.node.et.text ) )

FinetuningAction.register( CpAction )

class BuildenvCpAction(FinetuningAction):

    tag = 'buildenv_cp'

    def __init__(self, node):
        FinetuningAction.__init__(self, node)

    def execute(self, log, buildenv, target):
        log.do( "cp -av " + buildenv.rfs.fname( self.node.et.attrib['path'] ) + " " + buildenv.rfs.fname( self.node.et.text ) )

FinetuningAction.register( BuildenvCpAction )

class B2TCpAction(FinetuningAction):

    tag = 'b2t_cp'

    def __init__(self, node):
        FinetuningAction.__init__(self, node)

    def execute(self, log, buildenv, target):
        log.do( "cp -av " + buildenv.rfs.fname( self.node.et.attrib['path'] ) + " " + target.fname( self.node.et.text ) )

FinetuningAction.register( B2TCpAction )

class T2BCpAction(FinetuningAction):

    tag = 't2b_cp'

    def __init__(self, node):
        FinetuningAction.__init__(self, node)

    def execute(self, log, buildenv, target):
        log.do( "cp -av " + target.fname( self.node.et.attrib['path'] ) + " " + buildenv.rfs.fname( self.node.et.text ) )

FinetuningAction.register( T2BCpAction )

class T2PMvAction(FinetuningAction):

    tag = 't2p_mv'

    def __init__(self, node):
        FinetuningAction.__init__(self, node)

    def execute(self, log, buildenv, target):
        if self.node.et.text[0] == '/':
            dest = self.node.et.text[1:]
        else:
            dest = self.node.et.text
        dest = os.path.join ('..', dest)
        log.do( "mv -v " + target.fname( self.node.et.attrib['path'] ) + " " + dest )

FinetuningAction.register( T2PMvAction )

class MvAction(FinetuningAction):

    tag = 'mv'

    def __init__(self, node):
        FinetuningAction.__init__(self, node)

    def execute(self, log, buildenv, target):
        log.do( "mv -v " + target.fname( self.node.et.attrib['path'] ) + " " + target.fname( self.node.et.text ) )

FinetuningAction.register( MvAction )

class LnAction(FinetuningAction):

    tag = 'ln'

    def __init__(self, node):
        FinetuningAction.__init__(self, node)

    def execute(self, log, buildenv, target):
        with target:
            log.chroot (target.path, """/bin/sh -c 'ln -s %s "%s"' """ % (self.node.et.attrib['path'],
                                                      self.node.et.text))

FinetuningAction.register( LnAction )


class BuildenvMvAction(FinetuningAction):

    tag = 'buildenv_mv'

    def __init__(self, node):
        FinetuningAction.__init__(self, node)

    def execute(self, log, buildenv, target):
        log.do( "mv -v " + buildenv.rfs.fname( self.node.et.attrib['path'] ) + " " + buildenv.rfs.fname( self.node.et.text ) )

FinetuningAction.register( BuildenvMvAction )


class AddUserAction(FinetuningAction):

    tag = 'adduser'

    def __init__(self, node):
        FinetuningAction.__init__(self, node)

    def execute(self, log, buildenv, target):
      with target:
        if 'groups' in self.node.et.attrib:
          log.chroot (target.path, '/usr/sbin/useradd -U -m -G "%s" -s "%s" "%s"' % (
                self.node.et.attrib['groups'],
                self.node.et.attrib['shell'],
                self.node.et.text))
        else:
          log.chroot (target.path, '/usr/sbin/useradd -U -m -s "%s" "%s"' % (
                self.node.et.attrib['shell'], self.node.et.text))

        log.chroot( target.path,
             """/bin/sh -c 'echo "%s\\n%s\\n" | passwd %s'""" % (
                           self.node.et.attrib['passwd'],
                           self.node.et.attrib['passwd'],
                           self.node.et.text))

FinetuningAction.register( AddUserAction )


class AddGroupAction(FinetuningAction):

    tag = 'addgroup'

    def __init__(self, node):
        FinetuningAction.__init__(self, node)

    def execute(self, log, buildenv, target):
      with target:
        log.chroot (target.path, "/usr/sbin/groupadd -f %s" % (
            self.node.et.text))

FinetuningAction.register( AddGroupAction )

class RawCmdAction(FinetuningAction):

    tag = 'raw_cmd'

    def __init__(self, node):
        FinetuningAction.__init__(self, node)

    def execute(self, log, buildenv, target):
        with target:
            log.chroot (target.path, self.node.et.text)

FinetuningAction.register( RawCmdAction )

class CmdAction(FinetuningAction):

    tag = 'command'

    def __init__(self, node):
        FinetuningAction.__init__(self, node)

    def execute(self, log, buildenv, target):
        with target:
            log.chroot (target.path, "/bin/sh", input=self.node.et.text)

FinetuningAction.register( CmdAction )

class BuildenvCmdAction(FinetuningAction):

    tag = 'buildenv_command'

    def __init__(self, node):
        FinetuningAction.__init__(self, node)

    def execute(self, log, buildenv, target):
        with buildenv:
            log.chroot (buildenv.path, "/bin/sh", input=self.node.et.text)

FinetuningAction.register( BuildenvCmdAction )

class PurgeAction(FinetuningAction):

    tag = 'purge'

    def __init__(self, node):
        FinetuningAction.__init__(self, node)

    def execute(self, log, buildenv, target):
        with target:
            log.chroot (target.path, "dpkg --purge " + self.node.et.text)

FinetuningAction.register( PurgeAction )

class UpdatedAction(FinetuningAction):

    tag = 'updated'

    def __init__(self, node):
        FinetuningAction.__init__(self, node)

    def execute(self, log, buildenv, target):

        if self.node.et.text:
            fp = self.node.et.text
            log.printo ("transfer gpg key to target: " + fp)

            os.environ ['GNUPGHOME'] = "/var/cache/elbe/gnupg"
            key = BytesIO ()
            ctx = gpgme.Context ()
            ctx.armor = True
            ctx.export (fp, key)

            log.printo (str (key.getvalue ()))
            with open ((target.path + '/pub.key'), 'wb') as tkey:
                tkey.write (key.getvalue ())

            target.mkdir_p ("/var/cache/elbe/gnupg", mode=0700)
            with target:
                os.environ ['GNUPGHOME'] = target.path + "/var/cache/elbe/gnupg"
                log.do ("gpg --import " + target.path + "/pub.key")

        log.printo( "generate base repo")
        arch = target.xml.text ("project/arch", key="arch")

        buildenv.rfs.mkdir_p ('/tmp/pkgs')
        with buildenv:
            cache = get_rpcaptcache (buildenv.rfs, "updated-repo.log", arch)

            pkglist = cache.get_installed_pkgs()
            for pkg in pkglist:
                try:
                    cache.download_binary (pkg.name, '/tmp/pkgs', pkg.installed_version)
                except ValueError as ve:
                    log.printo( "No Package " + pkg.name + "-" + pkg.installed_version )
                except FetchError as fe:
                    log.printo( "Package " + pkg.name + "-" + pkg.installed_version + " could not be downloaded" )
                except TypeError as te:
                    log.printo( "Package " + pkg.name + "-" + pkg.installed_version + " missing name or version" )

        r = UpdateRepo (target.xml,
              target.path + '/var/cache/elbe/repos/base',
              log)

        for d in buildenv.rfs.glob ('tmp/pkgs/*.deb'):
            r.includedeb (d, 'main')
        r.finalize ()

        slist = target.path + '/etc/apt/sources.list.d/base.list'
        slist_txt = 'deb file:///var/cache/elbe/repos/base '
        slist_txt += target.xml.text ("/project/suite")
        slist_txt += " main"

        with open (slist, 'w') as apt_source:
            apt_source.write (slist_txt)

        rmtree (buildenv.rfs.path + '/tmp/pkgs')

        # allow downgrades by default
        target.touch_file ('/var/cache/elbe/.downgrade_allowed')

FinetuningAction.register( UpdatedAction )


def do_finetuning(xml, log, buildenv, target):

    if not xml.has('target/finetuning'):
        return

    for i in xml.node('target/finetuning'):
        try:
            action = FinetuningAction( i )
            action.execute(log, buildenv, target)
        except KeyError:
            print "Unimplemented finetuning action " + i.et.tag
        except CommandError:
            log.printo( "Finetuning Error, trying to continue anyways" )
