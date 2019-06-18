# ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (c) 2014-2017 Torben Hohn <torben.hohn@linutronix.de>
# Copyright (c) 2014-2017 Manuel Traut <manut@linutronix.de>
# Copyright (c) 2017 Philipp Arras <philipp.arras@linutronix.de>
# Copyright (c) 2017 Kurt Kanzenbach <kurt@linutronix.de>
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import print_function

import os
import logging

from shutil import rmtree
from gpg import core
from gpg.constants import PROTOCOL_OpenPGP
from apt.package import FetchError

from elbepack.repomanager import UpdateRepo
from elbepack.rpcaptcache import get_rpcaptcache
from elbepack.shellhelper import CommandError
from elbepack.filesystem import ImgMountFilesystem
from elbepack.packers import default_packer, packers
from elbepack.egpg import unlock_key
from elbepack.shellhelper import chroot, do, get_command_out


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

    def execute(self, _buildenv, _target):
        raise NotImplementedError('execute() not implemented')

    def execute_prj(self, buildenv, target, _builddir):
        self.execute(buildenv, target)


class ImageFinetuningAction(FinetuningAction):

    tag = 'image_finetuning'

    def __init__(self, node):
        FinetuningAction.__init__(self, node)

    def execute(self, _buildenv, _target):
        raise NotImplementedError("<%s> may only be "
                                  "used in <image-finetuning>" % self.tag)

    def execute_img(self, _buildenv, _target, _builddir, _loop_dev):
        raise NotImplementedError('execute_img() not implemented')


class RmAction(FinetuningAction):

    tag = 'rm'

    def __init__(self, node):
        FinetuningAction.__init__(self, node)

    def execute(self, _buildenv, target):
        files = target.glob(self.node.et.text)

        if 'exclude' in self.node.et.attrib:
            exclude = self.node.et.attrib['exclude'].split(' ')
        else:
            exclude = []

        for f in files:
            if os.path.basename(f) in exclude:
                continue

            do("rm -rvf '%s'" % f)


FinetuningAction.register(RmAction)


class MkdirAction(FinetuningAction):

    tag = 'mkdir'

    def __init__(self, node):
        FinetuningAction.__init__(self, node)

    def execute(self, _buildenv, target):
        do("mkdir -p %s" % target.fname(self.node.et.text))


FinetuningAction.register(MkdirAction)


class MknodAction(FinetuningAction):

    tag = 'mknod'

    def __init__(self, node):
        FinetuningAction.__init__(self, node)

    def execute(self, _buildenv, target):
        cmd = "mknod %s %s" % (target.fname(self.node.et.text),
                               self.node.et.attrib['opts'])
        do(cmd)


FinetuningAction.register(MknodAction)


class BuildenvMkdirAction(FinetuningAction):

    tag = 'buildenv_mkdir'

    def __init__(self, node):
        FinetuningAction.__init__(self, node)

    def execute(self, buildenv, _target):
        do("mkdir -p %s" % buildenv.rfs.fname(self.node.et.text))


FinetuningAction.register(BuildenvMkdirAction)


class CpAction(FinetuningAction):

    tag = 'cp'

    def __init__(self, node):
        FinetuningAction.__init__(self, node)

    def execute(self, _buildenv, target):
        src = target.glob(self.node.et.attrib['path'])
        for f in src:
            cmd = "cp -av %s %s" % (f, target.fname(self.node.et.text))
            do(cmd)


FinetuningAction.register(CpAction)


class BuildenvCpAction(FinetuningAction):

    tag = 'buildenv_cp'

    def __init__(self, node):
        FinetuningAction.__init__(self, node)

    def execute(self, buildenv, _target):
        src = buildenv.glob(self.node.et.attrib['path'])
        for f in src:
            # Does buildenv.rfs.fname(self.node.et.text) change in the
            # loop?  If not we can format the cmd outside of the loop
            # outside and make a smaller format in the loop.
            cmd = "cp -av %s %s" % (f, buildenv.rfs.fname(self.node.et.text))
            do(cmd)


FinetuningAction.register(BuildenvCpAction)


class B2TCpAction(FinetuningAction):

    tag = 'b2t_cp'

    def __init__(self, node):
        FinetuningAction.__init__(self, node)

    def execute(self, buildenv, target):
        src = buildenv.rfs.glob(self.node.et.attrib['path'])
        for f in src:
            cmd = "cp -av %s %s" % (f, target.fname(self.node.et.text))
            do(cmd)


FinetuningAction.register(B2TCpAction)


class T2BCpAction(FinetuningAction):

    tag = 't2b_cp'

    def __init__(self, node):
        FinetuningAction.__init__(self, node)

    def execute(self, buildenv, target):
        src = target.glob(self.node.et.attrib['path'])
        for f in src:
            cmd = "cp -av %s %s" % (f, buildenv.rfs.fname(self.node.et.text))
            do(cmd)


FinetuningAction.register(T2BCpAction)


class T2PMvAction(FinetuningAction):

    tag = 't2p_mv'

    def __init__(self, node):
        FinetuningAction.__init__(self, node)

    def execute(self, _buildenv, target):
        if self.node.et.text[0] == '/':
            dest = self.node.et.text[1:]
        else:
            dest = self.node.et.text
        dest = os.path.join('..', dest)

        src = target.glob(self.node.et.attrib['path'])
        cmd = "mv -v %s {}".format(dest)
        for f in src:
            do(cmd % f)


FinetuningAction.register(T2PMvAction)


class MvAction(FinetuningAction):

    tag = 'mv'

    def __init__(self, node):
        FinetuningAction.__init__(self, node)

    def execute(self, _buildenv, target):
        src = target.glob(self.node.et.attrib['path'])
        for f in src:
            cmd = "mv -v %s %s" % (f, target.fname(self.node.et.text))
            do(cmd)


FinetuningAction.register(MvAction)


class LnAction(FinetuningAction):

    tag = 'ln'

    def __init__(self, node):
        FinetuningAction.__init__(self, node)

    def execute(self, _buildenv, target):
        with target:
            cmd = """/bin/sh -c 'ln -s %s "%s"' """ % (self.node.et.attrib['path'],
                                                       self.node.et.text)
            chroot(target.path, cmd)

FinetuningAction.register(LnAction)


class BuildenvMvAction(FinetuningAction):

    tag = 'buildenv_mv'

    def __init__(self, node):
        FinetuningAction.__init__(self, node)

    def execute(self, buildenv, _target):
        src = buildenv.rfs.glob(self.node.et.attrib['path'])
        cmd = "mv -v %s %s"
        for f in src:
            do(cmd % (f, buildenv.rfs.fname(self.node.et.text)))

FinetuningAction.register(BuildenvMvAction)


class AddUserAction(FinetuningAction):

    tag = 'adduser'

    def __init__(self, node):
        FinetuningAction.__init__(self, node)

    def execute(self, _buildenv, target):
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

            cmd =  '/usr/sbin/useradd %s "%s"' % (options,
                                                  self.node.et.text)
            chroot(target.path, cmd)

            if 'passwd' in att:
                cmd = "passwd %s" % self.node.et.text
                stdin = "%s\n%s\n" % (att["passwd"], att["passwd"])
                chroot(target.path, cmd, stdin=stdin)


FinetuningAction.register(AddUserAction)


class AddGroupAction(FinetuningAction):

    tag = 'addgroup'

    def __init__(self, node):
        FinetuningAction.__init__(self, node)

    def execute(self, _buildenv, target):
        with target:
            att = self.node.et.attrib
            # we use -f always
            options = "-f "
            if 'gid' in att:
                options += '-g "%s" ' % att['gid']
            if 'system' in att and att['system'] == 'True':
                options += '-r'
            cmd = '/usr/sbin/groupadd %s "%s"' % (options,
                                                  self.node.et.text)
            chroot(target.path, cmd)


FinetuningAction.register(AddGroupAction)


class RawCmdAction(FinetuningAction):

    tag = 'raw_cmd'

    def __init__(self, node):
        FinetuningAction.__init__(self, node)

    def execute(self, _buildenv, target):
        with target:
            chroot(target.path, self.node.et.text)


FinetuningAction.register(RawCmdAction)


class CmdAction(FinetuningAction):

    tag = 'command'

    def __init__(self, node):
        FinetuningAction.__init__(self, node)

    def execute(self, _buildenv, target):
        with target:
            chroot(target.path, "/bin/sh", stdin=self.node.et.text)


FinetuningAction.register(CmdAction)


class BuildenvCmdAction(FinetuningAction):

    tag = 'buildenv_command'

    def __init__(self, node):
        FinetuningAction.__init__(self, node)

    def execute(self, buildenv, _target):
        with buildenv:
            chroot(buildenv.path, "/bin/sh", stdin=self.node.et.text)


FinetuningAction.register(BuildenvCmdAction)


class PurgeAction(FinetuningAction):

    tag = 'purge'

    def __init__(self, node):
        FinetuningAction.__init__(self, node)

    def execute(self, _buildenv, target):
        with target:
            chroot(target.path, "dpkg --purge %s" % (self.node.et.text))


FinetuningAction.register(PurgeAction)


class UpdatedAction(FinetuningAction):

    tag = 'updated'

    def __init__(self, node):
        FinetuningAction.__init__(self, node)

    def execute(self, buildenv, target):

        # pylint: disable=too-many-locals

        if self.node.et.text:
            fp = self.node.et.text

            logging.info("transfert gpg key to target: %s" % fp)

            gpgdata = core.Data()
            ctx = core.Context()
            ctx.set_engine_info(PROTOCOL_OpenPGP,
                                None,
                                '/var/cache/elbe/gnupg')
            ctx.set_armor(True)
            unlock_key(fp)
            ctx.op_export(fp, 0, gpgdata)
            gpgdata.seek(0, os.SEEK_SET)
            key = gpgdata.read()

            logging.info(str(key))
            with open((target.path + '/pub.key'), 'wb') as tkey:
                tkey.write(key)

            target.mkdir_p("/var/cache/elbe/gnupg", mode=0o700)
            with target:
                env_add = {'GNUPGHOME': target.path + "/var/cache/elbe/gnupg"}
                cmd = "gpg --import %s%s" % (target.path, "/pub.key")
                do(cmd, env_add=env_add)

        logging.info("generate base repo")

        arch = target.xml.text("project/arch", key="arch")

        buildenv.rfs.mkdir_p('/tmp/pkgs')
        with buildenv:
            cache = get_rpcaptcache(buildenv.rfs, arch)

            pkglist = cache.get_installed_pkgs()
            for pkg in pkglist:
                try:
                    cache.download_binary(
                        pkg.name, '/tmp/pkgs', pkg.installed_version)
                except ValueError:
                    logging.exception("No package %s-%s" % (pkg.name,
                                                            pkg.installed_version))
                except FetchError:
                    logging.exception("Package %s-%s could not be downloaded" % (pkg.name,
                                                                         pkg.installed_version))
                except TypeError:
                    logging.exception("Package %s-%s missing name or version" % (pkg.name,
                                                                                 pkg.installed_version))
        r = UpdateRepo(target.xml,
                       target.path + '/var/cache/elbe/repos/base')

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

    def execute(self, _buildenv, target):
        target.images.append('target' + self.node.et.text)

    def execute_prj(self, _buildenv, target, _builddir):
        target.images.append(self.node.et.text)


FinetuningAction.register(ArtifactAction)


class RmArtifactAction(FinetuningAction):

    tag = 'rm_artifact'

    def __init__(self, node):
        FinetuningAction.__init__(self, node)

    def execute(self, _buildenv, _target):
        raise NotImplementedError("<rm_artifact> may only be "
                                  "used in <project-finetuning>")

    def execute_prj(self, _buildenv, target, _builddir):
        target.images.remove(self.node.et.text)


FinetuningAction.register(ArtifactAction)


class LosetupAction(FinetuningAction):

    tag = 'losetup'

    def __init__(self, node):
        FinetuningAction.__init__(self, node)

    def execute(self, _buildenv, _target):
        raise NotImplementedError("<losetup> may only be "
                                  "used in <project-finetuning>")

    def execute_prj(self, buildenv, target, builddir):
        imgname = self.node.et.attrib['img']
        imgpath = os.path.join(builddir, imgname)
        cmd = 'losetup --find --show --partscan "%s"' % imgpath

        loop_dev = get_command_out(cmd).strip()
        try:
            for i in self.node:
                action = ImageFinetuningAction(i)
                action.execute_img(buildenv, target, builddir, loop_dev)
        finally:
            cmd = 'losetup --detach "%s"' % loop_dev
            do(cmd)


FinetuningAction.register(LosetupAction)


class ImgConvertAction(FinetuningAction):

    tag = 'img_convert'

    def __init__(self, node):
        FinetuningAction.__init__(self, node)

    def execute(self, _buildenv, _target):
        raise NotImplementedError("<img_convert> may only be "
                                  "used in <project-finetuning>")

    def execute_prj(self, _buildenv, target, builddir):
        src = self.node.et.text
        dst = self.node.et.attrib['dst']
        fmt = self.node.et.attrib['fmt']

        if src not in target.images:
            logging.error("Error: Artifact '%s' does not exist.\n Valid Artifcact are: %s" % (
                      src, ", ".join([str(i) for i in target.images])))
            raise FinetuningException("Artifact '%s' does not exist" % src)

        src_fname = os.path.join(builddir, src)
        dst_fname = os.path.join(builddir, dst)

        cmd = 'qemu-img convert -O "%s" "%s" "%s"' % (fmt,
                                                      src_fname,
                                                      dst_fname)
        do(cmd)

        target.images.append(dst)
        target.image_packers[dst] = default_packer

        if not self.node.bool_attr('keep_src'):
            target.images.remove(src)
            del target.image_packers[src]


FinetuningAction.register(ImgConvertAction)


class SetPackerAction(FinetuningAction):

    tag = 'set_packer'

    def __init__(self, node):
        FinetuningAction.__init__(self, node)

    def execute(self, _buildenv, _target):
        raise NotImplementedError("<set_packer> may only be "
                                  "used in <project-finetuning>")

    def execute_prj(self, _buildenv, target, _builddir):
        img = self.node.et.text
        packer = self.node.et.attrib['packer']

        target.image_packers[img] = packers[packer]


FinetuningAction.register(SetPackerAction)


class ExtractPartitionAction(ImageFinetuningAction):

    tag = 'extract_partition'

    def __init__(self, node):
        ImageFinetuningAction.__init__(self, node)

    def execute(self, _buildenv, _target):
        raise NotImplementedError("<extract_partition> may only be "
                                  "used in <mount_drive>")

    def execute_img(self, _buildenv, target, builddir, loop_dev):
        part_nr = self.node.et.attrib['part']
        imgname = os.path.join(builddir, self.node.et.text)

        cmd = 'dd if=%sp%s of="%s"' % (loop_dev, part_nr, imgname)

        do(cmd)

        target.images.append(self.node.et.text)
        target.image_packers[self.node.et.text] = default_packer


FinetuningAction.register(ExtractPartitionAction)


class CopyFromPartition(ImageFinetuningAction):

    tag = 'copy_from_partition'

    def __init__(self, node):
        ImageFinetuningAction.__init__(self, node)

    def execute(self, _buildenv, _target):
        raise NotImplementedError("<copy_from_partition> may only be "
                                  "used in <mount_drive>")

    def execute_img(self, _buildenv, target, builddir, loop_dev):
        part_nr = self.node.et.attrib['part']
        aname = self.node.et.attrib['artifact']

        img_mnt = os.path.join(builddir, 'imagemnt')
        device = "%sp%s" % (loop_dev, part_nr)

        with ImgMountFilesystem(img_mnt, device) as mnt_fs:
            fname = mnt_fs.glob(self.node.et.text)

            if not fname:
                logging.error('No file matching "%s" found' % self.node.et.text)
                raise FinetuningException('No File found')

            if len(fname) > 1:
                logging.info('Pattern "%s" matches %d files' % (self.node.et.text, len(fname)))
                raise FinetuningException('Patter matches too many files')

            cmd = 'cp "%s" "%s"' % (fname[0], os.path.join(builddir, aname))
            do(cmd)

            target.images.append(aname)


FinetuningAction.register(CopyFromPartition)


class CopyToPartition(ImageFinetuningAction):

    tag = 'copy_to_partition'

    def __init__(self, node):
        ImageFinetuningAction.__init__(self, node)

    def execute(self, _buildenv, _target):
        raise NotImplementedError("<copy_to_partition> may only be "
                                  "used in <mount_drive>")

    def execute_img(self, _buildenv, _target, builddir, loop_dev):
        part_nr = self.node.et.attrib['part']
        aname = self.node.et.attrib['artifact']

        img_mnt = os.path.join(builddir, 'imagemnt')
        device = "%sp%s" % (loop_dev, part_nr)

        with ImgMountFilesystem(img_mnt, device) as mnt_fs:
            fname = mnt_fs.fname(self.node.et.text)
            cmd = 'cp "%s" "%s"' % (os.path.join(builddir, aname), fname)
            do(cmd)


FinetuningAction.register(CopyToPartition)


def do_finetuning(xml, buildenv, target):

    if not xml.has('target/finetuning'):
        return

    for i in xml.node('target/finetuning'):
        try:
            action = FinetuningAction(i)
            action.execute(buildenv, target)
        except KeyError:
            logging.exception("Unimplemented finetuning action '%s'" % (i.et.tag))
        except CommandError:
            logging.exception("Finetuning Error, trying to continue anyways")
        except FinetuningException:
            logging.exception("Finetuning Error\n"
                              "Trying to continue anyways")

def do_prj_finetuning(xml, buildenv, target, builddir):

    if not xml.has('target/project-finetuning'):
        return

    for i in xml.node('target/project-finetuning'):
        try:
            action = FinetuningAction(i)
            action.execute_prj(buildenv, target, builddir)
        except KeyError:
            logging.exception("Unimplemented project-finetuning action '%s'" % (i.et.tag))
        except CommandError:
            logging.exception("ProjectFinetuning Error, trying to continue anyways")
        except FinetuningException:
            logging.exception("Finetuning Error\n"
                              "Trying to continue anyways")
