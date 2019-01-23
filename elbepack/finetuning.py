# ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (c) 2014-2017 Torben Hohn <torben.hohn@linutronix.de>
# Copyright (c) 2014-2017 Manuel Traut <manut@linutronix.de>
# Copyright (c) 2017 Philipp Arras <philipp.arras@linutronix.de>
# Copyright (c) 2017 Kurt Kanzenbach <kurt@linutronix.de>
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, print_function

import os

from shutil import rmtree

import gpg

from apt.package import FetchError

from elbepack.repomanager import UpdateRepo
from elbepack.rpcaptcache import get_rpcaptcache
from elbepack.shellhelper import CommandError


class FinetuningException(Exception):
    pass


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

    def execute(self, _log, _buildenv, _target):
        raise NotImplementedError('execute() not implemented')

    def execute_prj(self, log, buildenv, target, _builddir):
        self.execute(log, buildenv, target)


class ImageFinetuningAction(FinetuningAction):

    tag = 'image_finetuning'

    def __init__(self, node):
        FinetuningAction.__init__(self, node)

    def execute(self, _log, _buildenv, _target):
        raise NotImplementedError("<%s> may only be "
                                  "used in <image-finetuning>" % self.tag)

    def execute_img(self, _log, _buildenv, _target, _builddir, _loop_dev):
        raise NotImplementedError('execute_img() not implemented')


class RmAction(FinetuningAction):

    tag = 'rm'

    def __init__(self, node):
        FinetuningAction.__init__(self, node)

    def execute(self, log, _buildenv, target):
        files = target.glob(self.node.et.text)

        if 'exclude' in self.node.et.attrib:
            exclude = self.node.et.attrib['exclude'].split(' ')
        else:
            exclude = []

        for f in files:
            if os.path.basename(f) in exclude:
                continue

            log.do("rm -rvf '%s'" % f)


FinetuningAction.register(RmAction)


class MkdirAction(FinetuningAction):

    tag = 'mkdir'

    def __init__(self, node):
        FinetuningAction.__init__(self, node)

    def execute(self, log, _buildenv, target):
        log.do("mkdir -p " + target.fname(self.node.et.text))


FinetuningAction.register(MkdirAction)


class MknodAction(FinetuningAction):

    tag = 'mknod'

    def __init__(self, node):
        FinetuningAction.__init__(self, node)

    def execute(self, log, _buildenv, target):
        log.do(
            "mknod " +
            target.fname(
                self.node.et.text) +
            " " +
            self.node.et.attrib['opts'])


FinetuningAction.register(MknodAction)


class BuildenvMkdirAction(FinetuningAction):

    tag = 'buildenv_mkdir'

    def __init__(self, node):
        FinetuningAction.__init__(self, node)

    def execute(self, log, buildenv, _target):
        log.do("mkdir -p " + buildenv.rfs.fname(self.node.et.text))


FinetuningAction.register(BuildenvMkdirAction)


class CpAction(FinetuningAction):

    tag = 'cp'

    def __init__(self, node):
        FinetuningAction.__init__(self, node)

    def execute(self, log, _buildenv, target):
        src = target.glob(self.node.et.attrib['path'])
        for f in src:
            log.do("cp -av " + f + " " + target.fname(self.node.et.text))


FinetuningAction.register(CpAction)


class BuildenvCpAction(FinetuningAction):

    tag = 'buildenv_cp'

    def __init__(self, node):
        FinetuningAction.__init__(self, node)

    def execute(self, log, buildenv, _target):
        src = buildenv.glob(self.node.et.attrib['path'])
        for f in src:
            log.do("cp -av " + f + " " + buildenv.rfs.fname(self.node.et.text))


FinetuningAction.register(BuildenvCpAction)


class B2TCpAction(FinetuningAction):

    tag = 'b2t_cp'

    def __init__(self, node):
        FinetuningAction.__init__(self, node)

    def execute(self, log, buildenv, target):
        src = buildenv.rfs.glob(self.node.et.attrib['path'])
        for f in src:
            log.do("cp -av " + f + " " + target.fname(self.node.et.text))


FinetuningAction.register(B2TCpAction)


class T2BCpAction(FinetuningAction):

    tag = 't2b_cp'

    def __init__(self, node):
        FinetuningAction.__init__(self, node)

    def execute(self, log, buildenv, target):
        src = target.glob(self.node.et.attrib['path'])
        for f in src:
            log.do("cp -av " + f + " " + buildenv.rfs.fname(self.node.et.text))


FinetuningAction.register(T2BCpAction)


class T2PMvAction(FinetuningAction):

    tag = 't2p_mv'

    def __init__(self, node):
        FinetuningAction.__init__(self, node)

    def execute(self, log, _buildenv, target):
        if self.node.et.text[0] == '/':
            dest = self.node.et.text[1:]
        else:
            dest = self.node.et.text
        dest = os.path.join('..', dest)

        src = target.glob(self.node.et.attrib['path'])
        for f in src:
            log.do("mv -v " + f + " " + dest)


FinetuningAction.register(T2PMvAction)


class MvAction(FinetuningAction):

    tag = 'mv'

    def __init__(self, node):
        FinetuningAction.__init__(self, node)

    def execute(self, log, _buildenv, target):
        src = target.glob(self.node.et.attrib['path'])
        for f in src:
            log.do("mv -v " + f + " " + target.fname(self.node.et.text))


FinetuningAction.register(MvAction)


class LnAction(FinetuningAction):

    tag = 'ln'

    def __init__(self, node):
        FinetuningAction.__init__(self, node)

    def execute(self, log, _buildenv, target):
        with target:
            log.chroot(
                target.path, """/bin/sh -c 'ln -s %s "%s"' """ %
                (self.node.et.attrib['path'], self.node.et.text))


FinetuningAction.register(LnAction)


class BuildenvMvAction(FinetuningAction):

    tag = 'buildenv_mv'

    def __init__(self, node):
        FinetuningAction.__init__(self, node)

    def execute(self, log, buildenv, _target):
        src = buildenv.rfs.glob(self.node.et.attrib['path'])
        for f in src:
            log.do("mv -v " + f + " " + buildenv.rfs.fname(self.node.et.text))


FinetuningAction.register(BuildenvMvAction)


class AddUserAction(FinetuningAction):

    tag = 'adduser'

    def __init__(self, node):
        FinetuningAction.__init__(self, node)

    def execute(self, log, _buildenv, target):
        with target:
            att = self.node.et.attrib
            options = ""
            if 'groups' in att:
                options += '-G "%s" ' % att['groups']
            if 'shell' in att:
                options += '-s "%s" ' % att['shell']
            if 'uid' in att:
                options += '-u "%s" ' % att['uid']
            if 'gid' in att:
                options += '-g "%s" ' % att['gid']
            if 'home' in att:
                options += '-d "%s" ' % att['home']
            if 'system' in att and att['system'] == 'true':
                options += '-r'
            if 'create_home' in att and att['create_home'] == 'false':
                options += '-M '
            else:
                options += '-m '
            if 'create_group' in att and att['create_group'] == 'false':
                options += '-N '
            else:
                options += '-U '

            log.chroot(
                target.path,
                '/usr/sbin/useradd %s "%s"' %
                (options,
                 self.node.et.text))

            if 'passwd' in att:
                log.chroot(target.path,
                           """/bin/sh -c 'echo "%s\\n%s\\n" | passwd %s'""" % (
                               att['passwd'],
                               att['passwd'],
                               self.node.et.text))


FinetuningAction.register(AddUserAction)


class AddGroupAction(FinetuningAction):

    tag = 'addgroup'

    def __init__(self, node):
        FinetuningAction.__init__(self, node)

    def execute(self, log, _buildenv, target):
        with target:
            att = self.node.et.attrib
            # we use -f always
            options = "-f "
            if 'gid' in att:
                options += '-g "%s" ' % att['gid']
            if 'system' in att and att['system'] == 'True':
                options += '-r'
            log.chroot(target.path, '/usr/sbin/groupadd %s "%s"' % (
                options,
                self.node.et.text))


FinetuningAction.register(AddGroupAction)


class RawCmdAction(FinetuningAction):

    tag = 'raw_cmd'

    def __init__(self, node):
        FinetuningAction.__init__(self, node)

    def execute(self, log, _buildenv, target):
        with target:
            log.chroot(target.path, self.node.et.text)


FinetuningAction.register(RawCmdAction)


class CmdAction(FinetuningAction):

    tag = 'command'

    def __init__(self, node):
        FinetuningAction.__init__(self, node)

    def execute(self, log, _buildenv, target):
        with target:
            log.chroot(target.path, "/bin/sh", stdin=self.node.et.text)


FinetuningAction.register(CmdAction)


class BuildenvCmdAction(FinetuningAction):

    tag = 'buildenv_command'

    def __init__(self, node):
        FinetuningAction.__init__(self, node)

    def execute(self, log, buildenv, _target):
        with buildenv:
            log.chroot(buildenv.path, "/bin/sh", stdin=self.node.et.text)


FinetuningAction.register(BuildenvCmdAction)


class PurgeAction(FinetuningAction):

    tag = 'purge'

    def __init__(self, node):
        FinetuningAction.__init__(self, node)

    def execute(self, log, _buildenv, target):
        with target:
            log.chroot(target.path, "dpkg --purge " + self.node.et.text)


FinetuningAction.register(PurgeAction)


class UpdatedAction(FinetuningAction):

    tag = 'updated'

    def __init__(self, node):
        FinetuningAction.__init__(self, node)

    def execute(self, log, buildenv, target):

        # pylint: disable=too-many-locals

        if self.node.et.text:
            fp = self.node.et.text
            log.printo("transfer gpg key to target: " + fp)

            os.environ['GNUPGHOME'] = "/var/cache/elbe/gnupg"
            ctx = gpg.Context()
            ctx.armor = True
            key = ctx.key_export(fp)

            log.printo(key)
            with open((target.path + '/pub.key'), 'wb') as tkey:
                tkey.write(key)

            target.mkdir_p("/var/cache/elbe/gnupg", mode=0o700)
            with target:
                os.environ['GNUPGHOME'] = target.path + "/var/cache/elbe/gnupg"
                log.do("gpg --import " + target.path + "/pub.key")

        log.printo("generate base repo")
        arch = target.xml.text("project/arch", key="arch")

        buildenv.rfs.mkdir_p('/tmp/pkgs')
        with buildenv:
            cache = get_rpcaptcache(buildenv.rfs, "updated-repo.log", arch)

            pkglist = cache.get_installed_pkgs()
            for pkg in pkglist:
                try:
                    cache.download_binary(
                        pkg.name, '/tmp/pkgs', pkg.installed_version)
                except ValueError:
                    log.printo(
                        "No Package " +
                        pkg.name +
                        "-" +
                        pkg.installed_version)
                except FetchError:
                    log.printo(
                        "Package " +
                        pkg.name +
                        "-" +
                        pkg.installed_version +
                        " could not be downloaded")
                except TypeError:
                    log.printo(
                        "Package " +
                        pkg.name +
                        "-" +
                        pkg.installed_version +
                        " missing name or version")

        r = UpdateRepo(target.xml,
                       target.path + '/var/cache/elbe/repos/base',
                       log)

        for d in buildenv.rfs.glob('tmp/pkgs/*.deb'):
            r.includedeb(d, 'main')
        r.finalize()

        slist = target.path + '/etc/apt/sources.list.d/base.list'
        slist_txt = 'deb [trusted=yes] file:///var/cache/elbe/repos/base '
        slist_txt += target.xml.text("/project/suite")
        slist_txt += " main"

        with open(slist, 'w') as apt_source:
            apt_source.write(slist_txt)

        rmtree(buildenv.rfs.path + '/tmp/pkgs')

        # allow downgrades by default
        target.touch_file('/var/cache/elbe/.downgrade_allowed')


FinetuningAction.register(UpdatedAction)


class ArtifactAction(FinetuningAction):

    tag = 'artifact'

    def __init__(self, node):
        FinetuningAction.__init__(self, node)

    def execute(self, _log, _buildenv, target):
        target.images.append('target' + self.node.et.text)

    def execute_prj(self, _log, _buildenv, target, _builddir):
        target.images.append(self.node.et.text)


FinetuningAction.register(ArtifactAction)


class RmArtifactAction(FinetuningAction):

    tag = 'rm_artifact'

    def __init__(self, node):
        FinetuningAction.__init__(self, node)

    def execute(self, _log, _buildenv, _target):
        raise NotImplementedError("<rm_artifact> may only be "
                                  "used in <project-finetuning>")

    def execute_prj(self, _log, _buildenv, target, _builddir):
        target.images.remove(self.node.et.text)


FinetuningAction.register(ArtifactAction)


class LosetupAction(FinetuningAction):

    tag = 'losetup'

    def __init__(self, node):
        FinetuningAction.__init__(self, node)

    def execute(self, _log, _buildenv, _target):
        raise NotImplementedError("<losetup> may only be "
                                  "used in <project-finetuning>")

    def execute_prj(self, log, buildenv, target, builddir):
        imgname = self.node.et.attrib['img']
        imgpath = os.path.join(builddir, imgname)
        cmd = 'losetup --find --show --partscan "%s"' % imgpath

        loop_dev = log.get_command_out(cmd).strip()
        try:
            for i in self.node:
                action = ImageFinetuningAction(i)
                action.execute_img(log, buildenv, target, builddir, loop_dev)
        finally:
            cmd = 'losetup --detach "%s"' % loop_dev
            log.do(cmd)


FinetuningAction.register(LosetupAction)


class ImgConvertAction(FinetuningAction):

    tag = 'img_convert'

    def __init__(self, node):
        FinetuningAction.__init__(self, node)

    def execute(self, _log, _buildenv, _target):
        raise NotImplementedError("<img_convert> may only be "
                                  "used in <project-finetuning>")

    def execute_prj(self, log, _buildenv, target, builddir):
        src = self.node.et.text
        dst = self.node.et.attrib['dst']
        fmt = self.node.et.attrib['fmt']

        if src not in target.images:
            log.printo("Error: Artifact '%s' does not exist." % src)
            log.printo("Valid Artifacts are:")
            for i in target.images:
                log.printo(i)
            raise FinetuningException("Artifact '%s' does not exist" % src)

        src_fname = os.path.join(builddir, src)
        dst_fname = os.path.join(builddir, dst)

        cmd = 'qemu-img convert -O "%s" "%s" "%s"' % (fmt,
                                                      src_fname,
                                                      dst_fname)
        log.do(cmd)

        target.images.append(dst)
        target.image_packers[dst] = ('gzip -f', '.gz')

        if not self.node.bool_attr('keep_src'):
            target.images.remove(src)
            del target.image_packers[src]


FinetuningAction.register(ImgConvertAction)


class ExtractPartitionAction(ImageFinetuningAction):

    tag = 'extract_partition'

    def __init__(self, node):
        ImageFinetuningAction.__init__(self, node)

    def execute(self, _log, _buildenv, _target):
        raise NotImplementedError("<extract_partition> may only be "
                                  "used in <mount_drive>")

    def execute_img(self, log, _buildenv, target, builddir, loop_dev):
        part_nr = self.node.et.attrib['part']
        imgname = os.path.join(builddir, self.node.et.text)

        cmd = 'dd if=%sp%s of="%s"' % (loop_dev, part_nr, imgname)

        log.do(cmd)

        target.images.append(self.node.et.text)
        target.image_packers[self.node.et.text] = ('gzip -f', '.gz')


FinetuningAction.register(ExtractPartitionAction)


def do_finetuning(xml, log, buildenv, target):

    if not xml.has('target/finetuning'):
        return

    for i in xml.node('target/finetuning'):
        try:
            action = FinetuningAction(i)
            action.execute(log, buildenv, target)
        except KeyError:
            print("Unimplemented finetuning action '%s'" % (i.et.tag))
        except CommandError:
            log.printo("Finetuning Error, trying to continue anyways")
        except FinetuningException as e:
            log.printo("Finetuning Error: %s" % str(e))
            log.printo("trying to continue anyways")


def do_prj_finetuning(xml, log, buildenv, target, builddir):

    if not xml.has('target/project-finetuning'):
        return

    for i in xml.node('target/project-finetuning'):
        try:
            action = FinetuningAction(i)
            action.execute_prj(log, buildenv, target, builddir)
        except KeyError:
            print("Unimplemented project-finetuning action '%s'" % (i.et.tag))
        except CommandError:
            log.printo("ProjectFinetuning Error, trying to continue anyways")
        except FinetuningException as e:
            log.printo("ProjectFinetuning Error: %s" % e.message)
            log.printo("trying to continue anyways")
