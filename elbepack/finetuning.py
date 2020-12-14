# ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (c) 2014-2017 Torben Hohn <torben.hohn@linutronix.de>
# Copyright (c) 2014-2017 Manuel Traut <manut@linutronix.de>
# Copyright (c) 2017 Philipp Arras <philipp.arras@linutronix.de>
# Copyright (c) 2017 Kurt Kanzenbach <kurt@linutronix.de>
#
# SPDX-License-Identifier: GPL-3.0-or-later

import os
import errno
import base64
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
from elbepack.junit import TestSuite, TestException
from elbepack.shellhelper import chroot, do, get_command_out


class FinetuningException(Exception):
    pass

# TODO:py3 Remove object inheritance
# pylint: disable=useless-object-inheritance
class FinetuningAction(object):

    actiondict = {}

    tag = None

    @classmethod
    def register(cls, tag, register=True):
        def _register(action):
            action.tag = tag
            if register is True:
                cls.actiondict[tag] = action
            return action
        return _register

    def __new__(cls, node):
        if node.tag not in cls.actiondict:
            raise FinetuningException("Invalid finetuning action %s" %
                                      node.tag)
        action = cls.actiondict[node.tag]
        return object.__new__(action)

    def __init__(self, node):
        self.node = node

    def execute(self, _buildenv, _target):
        raise NotImplementedError('execute() not implemented')

    def execute_prj(self, buildenv, target, _builddir):
        self.execute(buildenv, target)


@FinetuningAction.register('image_finetuning', False)
class ImageFinetuningAction(FinetuningAction):

    def __init__(self, node):
        FinetuningAction.__init__(self, node)

    def execute(self, _buildenv, _target):
        raise NotImplementedError("<%s> may only be "
                                  "used in <image-finetuning>" % self.tag)

    def execute_img(self, _buildenv, _target, _builddir, _loop_dev):
        raise NotImplementedError('execute_img() not implemented')


@FinetuningAction.register('rm')
class RmAction(FinetuningAction):

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


@FinetuningAction.register('mkdir')
class MkdirAction(FinetuningAction):

    def __init__(self, node):
        FinetuningAction.__init__(self, node)

    def execute(self, _buildenv, target):
        do("mkdir -p %s" % target.fname(self.node.et.text))


@FinetuningAction.register('mknod')
class MknodAction(FinetuningAction):

    def __init__(self, node):
        FinetuningAction.__init__(self, node)

    def execute(self, _buildenv, target):
        cmd = "mknod %s %s" % (target.fname(self.node.et.text),
                               self.node.et.attrib['opts'])
        do(cmd)


@FinetuningAction.register('buildenv_mkdir')
class BuildenvMkdirAction(FinetuningAction):

    def __init__(self, node):
        FinetuningAction.__init__(self, node)

    def execute(self, buildenv, _target):
        do("mkdir -p %s" % buildenv.rfs.fname(self.node.et.text))


@FinetuningAction.register('cp')
class CpAction(FinetuningAction):

    def __init__(self, node):
        FinetuningAction.__init__(self, node)

    def execute(self, _buildenv, target):
        src = target.glob(self.node.et.attrib['path'])
        cmd = "cp -av %s {}".format(target.fname(self.node.et.text))
        for f in src:
            do(cmd % f)


@FinetuningAction.register('buildenv_cp')
class BuildenvCpAction(FinetuningAction):

    def __init__(self, node):
        FinetuningAction.__init__(self, node)

    def execute(self, buildenv, _target):
        src = buildenv.glob(self.node.et.attrib['path'])
        cmd = "cp -av %s {}".format(buildenv.rfs.fname(self.node.et.text))
        for f in src:
            do(cmd % f)


@FinetuningAction.register('b2t_cp')
class B2TCpAction(FinetuningAction):

    def __init__(self, node):
        FinetuningAction.__init__(self, node)

    def execute(self, buildenv, target):
        src = buildenv.rfs.glob(self.node.et.attrib['path'])
        cmd = "cp -av %s {}".format(target.fname(self.node.et.text))
        for f in src:
            do(cmd % f)


@FinetuningAction.register('t2b_cp')
class T2BCpAction(FinetuningAction):

    def __init__(self, node):
        FinetuningAction.__init__(self, node)

    def execute(self, buildenv, target):
        src = target.glob(self.node.et.attrib['path'])
        cmd = "cp -av %s {}".format(buildenv.rfs.fname(self.node.et.text))
        for f in src:
            do(cmd % f)


@FinetuningAction.register('t2p_mv')
class T2PMvAction(FinetuningAction):

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


@FinetuningAction.register('mv')
class MvAction(FinetuningAction):

    def __init__(self, node):
        FinetuningAction.__init__(self, node)

    def execute(self, _buildenv, target):
        src = target.glob(self.node.et.attrib['path'])
        cmd = "mv -v %s {}".format(target.fname(self.node.et.text))
        for f in src:
            do(cmd % f)


@FinetuningAction.register('ln')
class LnAction(FinetuningAction):

    def __init__(self, node):
        FinetuningAction.__init__(self, node)

    def execute(self, _buildenv, target):
        target_name = self.node.et.attrib['path']
        link_name = self.node.et.text
        with target.protect({link_name}):
            chroot(target.path,
                   """/bin/sh -c 'ln -sf %s "%s"' """ %
                   (target_name, link_name))


@FinetuningAction.register('buildenv_mv')
class BuildenvMvAction(FinetuningAction):

    def __init__(self, node):
        FinetuningAction.__init__(self, node)

    def execute(self, buildenv, _target):
        src = buildenv.rfs.glob(self.node.et.attrib['path'])
        cmd = "mv -v %s {}".format(buildenv.rfs.fname(self.node.et.text))
        for f in src:
            do(cmd % f)


@FinetuningAction.register('adduser')
class AddUserAction(FinetuningAction):

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

            cmd = '/usr/sbin/useradd %s "%s"' % (options,
                                                 self.node.et.text)
            chroot(target.path, cmd)

            if 'passwd' in att:
                cmd = "passwd %s" % self.node.et.text
                stdin = "%s\n%s\n" % (att["passwd"], att["passwd"])
                chroot(target.path, cmd, stdin=stdin)


@FinetuningAction.register('addgroup')
class AddGroupAction(FinetuningAction):

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


@FinetuningAction.register('file')
class AddFileAction(FinetuningAction):

    def __init__(self, node):
        FinetuningAction.__init__(self, node)

    @staticmethod
    def decode(text, encoding):
        if encoding == "plain":
            msg = "\n".join([line.lstrip(" \t")
                             for line in text.splitlines()[1:-1]])
        elif encoding == "raw":
            msg = "\n".join(text.splitlines()[1:-1])
        elif encoding == "base64":
            msg = base64.standard_b64decode(text)
        else:
            raise FinetuningException("Invalid encoding %s" % encoding)
        return msg

    def execute(self, _buildenv, target):

        att = self.node.et.attrib
        dst = att["dst"]
        content = self.node.et.text
        encoding = "plain"
        owner = None
        group = None
        mode = None

        if "encoding" in att:
            encoding = att["encoding"]
        if "owner" in att:
            owner = att["owner"]
        if "group" in att:
            group = att["group"]
        if "mode" in att:
            mode = att["mode"]

        try:
            target.mkdir_p(os.path.dirname(dst))
        except OSError as E:
            if E.errno is not errno.EEXIST:
                raise

        content = AddFileAction.decode(content, encoding)

        if "append" in att and att["append"] == "true":
            target.append_file(dst, content)
        else:
            target.write_file(dst, None, content)

        if owner is not None:
            chroot(target.path, 'chown "%s" "%s"' % (owner, dst))

        if group is not None:
            chroot(target.path, 'chgrp "%s" "%s"' % (group, dst))

        if mode is not None:
            chroot(target.path, 'chmod "%s" "%s"' % (mode, dst))


@FinetuningAction.register('raw_cmd')
class RawCmdAction(FinetuningAction):

    def __init__(self, node):
        FinetuningAction.__init__(self, node)

    def execute(self, _buildenv, target):
        with target:
            chroot(target.path, self.node.et.text)


@FinetuningAction.register('command')
class CmdAction(ImageFinetuningAction):

    def __init__(self, node):
        ImageFinetuningAction.__init__(self, node)

    def execute_img(self, _buildenv, _target, builddir, loop_dev):

        script = '\n'.join(line.lstrip(" \t")
                           for line
                           in self.node.et.text.strip("\n").splitlines())

        mnt   = os.path.join(builddir, 'imagemnt')
        dev   = "%sp%s" % (loop_dev, self.node.et.attrib["part"])

        with ImgMountFilesystem(mnt, dev) as fs:
            do("/bin/sh", stdin=script,
               env_add={"ELBE_MNT": fs.path})

    def execute(self, _buildenv, target):
        with target:
            chroot(target.path, "/bin/sh", stdin=self.node.et.text)


@FinetuningAction.register('buildenv_command')
class BuildenvCmdAction(FinetuningAction):

    def __init__(self, node):
        FinetuningAction.__init__(self, node)

    def execute(self, buildenv, _target):
        with buildenv:
            chroot(buildenv.path, "/bin/sh", stdin=self.node.et.text)


@FinetuningAction.register('purge')
class PurgeAction(FinetuningAction):

    def __init__(self, node):
        FinetuningAction.__init__(self, node)

    def execute(self, _buildenv, target):
        with target:
            chroot(target.path, "dpkg --purge %s" % (self.node.et.text))


@FinetuningAction.register('updated')
class UpdatedAction(FinetuningAction):

    def __init__(self, node):
        FinetuningAction.__init__(self, node)

    def execute(self, buildenv, target):

        # pylint: disable=too-many-locals

        if self.node.et.text:
            fp = self.node.et.text

            logging.info("transfert gpg key to target: %s", fp)

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
                    logging.exception("No package %s-%s",
                                      pkg.name, pkg.installed_version)
                except FetchError:
                    logging.exception("Package %s-%s could not be downloaded",
                                      pkg.name, pkg.installed_version)
                except TypeError:
                    logging.exception("Package %s-%s missing name or version",
                                      pkg.name, pkg.installed_version)
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


@FinetuningAction.register('artifact')
class ArtifactAction(FinetuningAction):

    def __init__(self, node):
        FinetuningAction.__init__(self, node)

    def execute(self, buildenv, target):
        if os.path.isfile("../target/" + self.node.et.text):
            target.images.append('target' + self.node.et.text)
        else:
            logging.error("The specified artifact: '%s' doesn't exist" %
                           self.node.et.text)

    def execute_prj(self, buildenv, target, builddir):
        if os.path.isfile("../" + self.node.et.text):
            target.images.append(self.node.et.text)
        else:
            logging.error("The specified artifact: '%s' doesn't exist" %
                           self.node.et.text)


@FinetuningAction.register('rm_artifact')
class RmArtifactAction(FinetuningAction):

    def __init__(self, node):
        FinetuningAction.__init__(self, node)

    def execute(self, _buildenv, _target):
        raise NotImplementedError("<rm_artifact> may only be "
                                  "used in <project-finetuning>")

    def execute_prj(self, _buildenv, target, _builddir):
        try:
            target.images.remove(self.node.et.text)
        except ValueError:
            raise FinetuningException("Artifact %s doesn't exist" %
                                      self.node.et.text)


@FinetuningAction.register('losetup')
class LosetupAction(FinetuningAction):

    def __init__(self, node):
        FinetuningAction.__init__(self, node)

    def execute(self, _buildenv, _target):
        raise NotImplementedError("<losetup> may only be "
                                  "used in <project-finetuning>")

    def execute_prj(self, buildenv, target, builddir):
        imgname = self.node.et.attrib['img']
        imgpath = os.path.join(builddir, imgname)
        cmd = 'losetup --find --show --partscan "%s"' % imgpath

        loop_dev = get_command_out(cmd).decode().strip()
        try:
            for i in self.node:
                action = ImageFinetuningAction(i)
                action.execute_img(buildenv, target, builddir, loop_dev)
        finally:
            cmd = 'losetup --detach "%s"' % loop_dev
            do(cmd)


@FinetuningAction.register('img_convert')
class ImgConvertAction(FinetuningAction):

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
            logging.error("Artifact '%s' does not exist.\n"
                          "Valid Artifcact are: %s",
                          src, ", ".join([str(i) for i in target.images]))
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


@FinetuningAction.register('set_packer')
class SetPackerAction(FinetuningAction):

    def __init__(self, node):
        FinetuningAction.__init__(self, node)

    def execute(self, _buildenv, _target):
        raise NotImplementedError("<set_packer> may only be "
                                  "used in <project-finetuning>")

    def execute_prj(self, _buildenv, target, _builddir):
        img = self.node.et.text
        packer = self.node.et.attrib['packer']

        target.image_packers[img] = packers[packer]


@FinetuningAction.register('extract_partition')
class ExtractPartitionAction(ImageFinetuningAction):

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


@FinetuningAction.register('copy_from_partition')
class CopyFromPartition(ImageFinetuningAction):

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
                logging.error('No file matching "%s" found',
                              self.node.et.text)
                raise FinetuningException('No File found')

            if len(fname) > 1:
                logging.info('Pattern "%s" matches %d files',
                             self.node.et.text, len(fname))
                raise FinetuningException('Patter matches too many files')

            cmd = 'cp "%s" "%s"' % (fname[0], os.path.join(builddir, aname))
            do(cmd)

            target.images.append(aname)


@FinetuningAction.register('copy_to_partition')
class CopyToPartition(ImageFinetuningAction):

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

@FinetuningAction.register('set_partition_type')
class SetPartitionTypeAction(ImageFinetuningAction):

    def __init__(self, node):
        ImageFinetuningAction.__init__(self, node)

    def execute(self, _buildenv, _target):
        raise NotImplementedError("<set_partition_type> may only be "
                                  "used in <mount_drive>")

    def execute_img(self, _buildenv, target, builddir, loop_dev):
        part_nr = self.node.et.attrib['part']
        part_type = self.node.et.attrib['type']

        cmd = f'fdisk {loop_dev}'
        inp = f't\n{part_nr}\n{part_type}\nw\n'

        do(cmd, stdin=inp)


@FinetuningAction.register("unit-tests")
class TestSuites(FinetuningAction):

    elbe_junit = "elbe-junit.xml"

    def execute(self, _buildenv, _target):
        raise NotImplementedError("<%s> can only be used in the context of a project" %
                                  self.tag)

    def execute_prj(self, buildenv, target, builddir):

        tss = []
        output = os.path.join(builddir, self.elbe_junit)
        target.images.append(self.elbe_junit)

        for test_suite in self.node:
            ts = TestSuite(test_suite, target)
            try:
                tss.append(ts())
            except TestException as E:
                logging.exception(str(E))

        TestSuite.to_file(output, tss)


@FinetuningAction.register("rm_apt_source")
class RmAptSource(FinetuningAction):

    def execute(self, buildenv, _target):

        src_path = "%s/../target/etc/apt/sources.list" % buildenv.path

        with open(src_path, "r") as f:
            src_lst = f.read().split("\n")

        rm_src = self.node.et.text.replace("LOCALMACHINE", "10.0.2.2")
        src_lst = [src for src in src_lst if rm_src not in src]

        with open(src_path, "w") as f:
            f.write("\n".join(src_lst))


def do_finetuning(xml, buildenv, target):

    if not xml.has('target/finetuning'):
        return

    for i in xml.node('target/finetuning'):
        try:
            action = FinetuningAction(i)
        except KeyError:
            logging.exception("Unimplemented finetuning action '%s'",
                              i.et.tag)
            return
        try:
            action.execute(buildenv, target)
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
            logging.exception("Unimplemented project-finetuning action '%s'",
                              i.et.tag)
        except CommandError:
            logging.exception("ProjectFinetuning Error, "
                              "trying to continue anyways")
        except FinetuningException:
            logging.exception("Finetuning Error\n"
                              "Trying to continue anyways")
        except Exception as e:
            logging.exception(str(e))
            raise
