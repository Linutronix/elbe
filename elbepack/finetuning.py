# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2014-2017 Linutronix GmbH

import base64
import errno
import logging
import os
import shlex
import subprocess
from shutil import rmtree

from apt.package import FetchError

from gpg import core
from gpg.constants import PROTOCOL_OpenPGP

from elbepack.egpg import unlock_key
from elbepack.filesystem import Filesystem
from elbepack.imgutils import losetup, mount
from elbepack.packers import default_packer, packers
from elbepack.repomanager import UpdateRepo
from elbepack.rpcaptcache import get_rpcaptcache
from elbepack.shellhelper import chroot, do


class FinetuningException(Exception):
    pass


class FinetuningAction:

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
            raise FinetuningException(f'Invalid finetuning action {node.tag}')
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

    def execute(self, _buildenv, _target):
        raise NotImplementedError(
            f'<{self.tag}> may only be used in <image-finetuning>')

    def execute_img(self, _buildenv, _target, _builddir, _loop_dev):
        raise NotImplementedError('execute_img() not implemented')


@FinetuningAction.register('rm')
class RmAction(FinetuningAction):

    def execute(self, _buildenv, target):
        files = target.glob(self.node.et.text)

        if 'exclude' in self.node.et.attrib:
            exclude = self.node.et.attrib['exclude'].split(' ')
        else:
            exclude = []

        for f in files:
            if os.path.basename(f) in exclude:
                continue

            do(['rm', '-rvf', f])


@FinetuningAction.register('mkdir')
class MkdirAction(FinetuningAction):

    def execute(self, _buildenv, target):
        do(['mkdir', '-p', target.fname(self.node.et.text)])


@FinetuningAction.register('mknod')
class MknodAction(FinetuningAction):

    def execute(self, _buildenv, target):
        do(['mknod', target.fname(self.node.et.text), *shlex.split(self.node.et.attrib['opts'])])


@FinetuningAction.register('buildenv_mkdir')
class BuildenvMkdirAction(FinetuningAction):

    def execute(self, buildenv, _target):
        do(['mkdir', '-p', buildenv.rfs.fname(self.node.et.text)])


@FinetuningAction.register('cp')
class CpAction(FinetuningAction):

    def execute(self, _buildenv, target):
        src = target.glob(self.node.et.attrib['path'])
        for f in src:
            do(['cp', '-av', f, target.fname(self.node.et.text)])


@FinetuningAction.register('buildenv_cp')
class BuildenvCpAction(FinetuningAction):

    def execute(self, buildenv, _target):
        src = buildenv.glob(self.node.et.attrib['path'])
        for f in src:
            do(['cp', '-av', f, buildenv.rfs.fname(self.node.et.text)])


@FinetuningAction.register('b2t_cp')
class B2TCpAction(FinetuningAction):

    def execute(self, buildenv, target):
        src = buildenv.rfs.glob(self.node.et.attrib['path'])
        for f in src:
            do(['cp', '-av', f, target.fname(self.node.et.text)])


@FinetuningAction.register('t2b_cp')
class T2BCpAction(FinetuningAction):

    def execute(self, buildenv, target):
        src = target.glob(self.node.et.attrib['path'])
        for f in src:
            do(['cp', '-av', f, buildenv.rfs.fname(self.node.et.text)])


@FinetuningAction.register('t2p_mv')
class T2PMvAction(FinetuningAction):

    def execute(self, _buildenv, target):
        if self.node.et.text[0] == '/':
            dest = self.node.et.text[1:]
        else:
            dest = self.node.et.text
        dest = os.path.join('..', dest)

        src = target.glob(self.node.et.attrib['path'])
        for f in src:
            do(['mv', '-v', f, dest])


@FinetuningAction.register('mv')
class MvAction(FinetuningAction):

    def execute(self, _buildenv, target):
        src = target.glob(self.node.et.attrib['path'])
        for f in src:
            do(['mv', '-v', f, target.fname(self.node.et.text)])


@FinetuningAction.register('ln')
class LnAction(FinetuningAction):

    def execute(self, _buildenv, target):
        target_name = self.node.et.attrib['path']
        link_name = self.node.et.text
        chroot(target.path, ['ln', '-sf', target_name, link_name])


@FinetuningAction.register('buildenv_mv')
class BuildenvMvAction(FinetuningAction):

    def execute(self, buildenv, _target):
        src = buildenv.rfs.glob(self.node.et.attrib['path'])
        for f in src:
            do(['mv', '-v', f, buildenv.rfs.fname(self.node.et.text)])


@FinetuningAction.register('adduser')
class AddUserAction(FinetuningAction):

    def execute(self, _buildenv, target):
        with target:
            att = self.node.et.attrib
            options = []
            if 'groups' in att:
                options.extend(['-G',  att['groups']])
            if 'shell' in att:
                options.extend(['-s',  att['shell']])
            if 'uid' in att:
                options.extend(['-u',  att['uid']])
            if 'gid' in att:
                options.extend(['-g',  att['gid']])
            if 'home' in att:
                options.extend(['-d',  att['home']])
            if self.node.bool_attr('system'):
                options.append('-r')
            if 'create_home' in att and att['create_home'] == 'false':
                options.append('-M')
            else:
                options.append('-m')
            if 'create_group' in att and att['create_group'] == 'false':
                options.append('-N')
            else:
                options.append('-U')

            chroot(target.path, ['/usr/sbin/useradd', *options, self.node.et.text])

            if 'passwd_hashed' in att:
                chroot(target.path, ['chpasswd', '--encrypted'],
                       input=f"{self.node.et.text}:{att['passwd_hashed']}".encode('ascii'))


@FinetuningAction.register('addgroup')
class AddGroupAction(FinetuningAction):

    def execute(self, _buildenv, target):
        with target:
            att = self.node.et.attrib
            # we use -f always
            options = ['-f']
            if 'gid' in att:
                options.extend(['-g', att['gid']])
            if self.node.bool_attr('system'):
                options.append('-r')
            chroot(target.path, ['/usr/sbin/groupadd', *options, self.node.et.text])


@FinetuningAction.register('file')
class AddFileAction(FinetuningAction):

    @staticmethod
    def decode(text, encoding):
        if encoding == 'plain':
            msg = '\n'.join([line.lstrip(' \t')
                             for line in text.splitlines()[1:-1]])
        elif encoding == 'raw':
            msg = '\n'.join(text.splitlines()[1:-1])
        elif encoding == 'base64':
            msg = base64.standard_b64decode(text)
        else:
            raise FinetuningException(f'Invalid encoding {encoding}')
        return msg

    def execute(self, _buildenv, target):

        att = self.node.et.attrib
        dst = att['dst']
        content = self.node.et.text
        encoding = 'plain'
        owner = None
        group = None
        mode = None

        if 'encoding' in att:
            encoding = att['encoding']
        if 'owner' in att:
            owner = att['owner']
        if 'group' in att:
            group = att['group']
        if 'mode' in att:
            mode = att['mode']

        try:
            target.mkdir_p(os.path.dirname(dst))
        except OSError as E:
            if E.errno is not errno.EEXIST:
                raise

        content = AddFileAction.decode(content, encoding)

        if self.node.bool_attr('append'):
            target.append_file(dst, content)
        else:
            target.write_file(dst, None, content)

        if owner is not None:
            chroot(target.path, ['chown', owner, dst])

        if group is not None:
            chroot(target.path, ['chgrp', group, dst])

        if mode is not None:
            chroot(target.path, ['chmod', mode, dst])


@FinetuningAction.register('raw_cmd')
class RawCmdAction(FinetuningAction):

    def execute(self, _buildenv, target):
        with target:
            chroot(target.path, shlex.split(self.node.et.text))


@FinetuningAction.register('command')
class CmdAction(ImageFinetuningAction):

    def execute_img(self, _buildenv, _target, builddir, loop_dev):

        script = '\n'.join(line.lstrip(' \t')
                           for line
                           in self.node.et.text.strip('\n').splitlines())

        mnt = os.path.join(builddir, 'imagemnt')
        dev = f"{loop_dev}p{self.node.et.attrib['part']}"

        if self.node.bool_attr('nomount'):
            do(['/bin/sh'], input=script.encode('ascii'),
               env_add={'ELBE_DEV': dev},
               log_cmd=script)
        else:
            with mount(dev, mnt):
                do(['/bin/sh'], input=script.encode('ascii'),
                   env_add={'ELBE_MNT': mnt},
                   log_cmd=script)

    def execute(self, _buildenv, target):
        with target:
            chroot(target.path, '/bin/sh', input=self.node.et.text.encode('ascii'),
                   log_cmd=self.node.et.text)


@FinetuningAction.register('buildenv_command')
class BuildenvCmdAction(FinetuningAction):

    def execute(self, buildenv, _target):
        with buildenv:
            chroot(buildenv.path, '/bin/sh', input=self.node.et.text.encode('ascii'))


@FinetuningAction.register('purge')
class PurgeAction(FinetuningAction):

    def execute(self, _buildenv, target):
        with target:
            chroot(target.path, f'dpkg --purge {self.node.et.text}')


@FinetuningAction.register('updated')
class UpdatedAction(FinetuningAction):

    def execute(self, buildenv, target):

        if self.node.et.text:
            fp = self.node.et.text

            logging.info('transfert gpg key to target: %s', fp)

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

            target.mkdir_p('/var/cache/elbe/gnupg', mode=0o700)
            with target:
                do(['gpg', '--import', target.path + '/pub.key'],
                    env_add={'GNUPGHOME': f'{target.path}/var/cache/elbe/gnupg'})

        logging.info('generate base repo')

        arch = target.xml.text('project/arch', key='arch')

        buildenv.rfs.mkdir_p('/tmp/pkgs')
        with buildenv:
            cache = get_rpcaptcache(buildenv.rfs, arch)

            pkglist = cache.get_installed_pkgs()
            for pkg in pkglist:
                try:
                    cache.download_binary(
                        pkg.name, '/tmp/pkgs', pkg.installed_version)
                except ValueError:
                    logging.exception('No package %s-%s',
                                      pkg.name, pkg.installed_version)
                except FetchError:
                    logging.exception('Package %s-%s could not be downloaded',
                                      pkg.name, pkg.installed_version)
                except TypeError:
                    logging.exception('Package %s-%s missing name or version',
                                      pkg.name, pkg.installed_version)
        r = UpdateRepo(target.xml,
                       target.path + '/var/cache/elbe/repos/base')

        for d in buildenv.rfs.glob('tmp/pkgs/*.deb'):
            r.includedeb(d, 'main')
        r.finalize()

        slist = target.path + '/etc/apt/sources.list.d/base.list'
        slist_txt = 'deb [trusted=yes] file:///var/cache/elbe/repos/base '
        slist_txt += target.xml.text('/project/suite')
        slist_txt += ' main'

        with open(slist, 'w') as apt_source:
            apt_source.write(slist_txt)

        rmtree(buildenv.rfs.path + '/tmp/pkgs')

        # allow downgrades by default
        target.touch_file('/var/cache/elbe/.downgrade_allowed')


@FinetuningAction.register('artifact')
class ArtifactAction(FinetuningAction):

    def execute(self, _buildenv, target):
        if os.path.isfile('../target/' + self.node.et.text):
            target.images.append('target' + self.node.et.text)
        else:
            logging.error("The specified artifact: '%s' doesn't exist",
                          self.node.et.text)

    def execute_prj(self, _buildenv, target, _builddir):
        if os.path.isfile('../' + self.node.et.text):
            target.images.append(self.node.et.text)
        else:
            logging.error("The specified artifact: '%s' doesn't exist",
                          self.node.et.text)


@FinetuningAction.register('rm_artifact')
class RmArtifactAction(FinetuningAction):

    def execute(self, _buildenv, _target):
        raise NotImplementedError('<rm_artifact> may only be '
                                  'used in <project-finetuning>')

    def execute_prj(self, _buildenv, target, _builddir):
        try:
            target.images.remove(self.node.et.text)
        except ValueError:
            raise FinetuningException(
                f"Artifact {self.node.et.text} doesn't exist")


@FinetuningAction.register('losetup')
class LosetupAction(FinetuningAction):

    def execute(self, _buildenv, _target):
        raise NotImplementedError('<losetup> may only be '
                                  'used in <project-finetuning>')

    def execute_prj(self, buildenv, target, builddir):
        imgname = self.node.et.attrib['img']
        imgpath = os.path.join(builddir, imgname)

        with losetup(imgpath) as loop_dev:
            for i in self.node:
                action = ImageFinetuningAction(i)
                action.execute_img(buildenv, target, builddir, loop_dev)


@FinetuningAction.register('img_convert')
class ImgConvertAction(FinetuningAction):

    def execute(self, _buildenv, _target):
        raise NotImplementedError('<img_convert> may only be '
                                  'used in <project-finetuning>')

    def execute_prj(self, _buildenv, target, builddir):
        src = self.node.et.text
        dst = self.node.et.attrib['dst']
        fmt = self.node.et.attrib['fmt']

        if src not in target.images:
            logging.error("Artifact '%s' does not exist.\n"
                          'Valid Artifcact are: %s',
                          src, ', '.join([str(i) for i in target.images]))
            raise FinetuningException(f"Artifact '{src}' does not exist")

        src_fname = os.path.join(builddir, src)
        dst_fname = os.path.join(builddir, dst)

        do(['qemu-img', 'convert', '-O', fmt, src_fname, dst_fname])

        target.images.append(dst)
        target.image_packers[dst] = default_packer

        if not self.node.bool_attr('keep_src'):
            target.images.remove(src)
            del target.image_packers[src]


@FinetuningAction.register('set_packer')
class SetPackerAction(FinetuningAction):

    def execute(self, _buildenv, _target):
        raise NotImplementedError('<set_packer> may only be '
                                  'used in <project-finetuning>')

    def execute_prj(self, _buildenv, target, _builddir):
        img = self.node.et.text
        packer = self.node.et.attrib['packer']

        target.image_packers[img] = packers[packer]


@FinetuningAction.register('extract_partition')
class ExtractPartitionAction(ImageFinetuningAction):

    def execute(self, _buildenv, _target):
        raise NotImplementedError('<extract_partition> may only be '
                                  'used in <losetup>')

    def execute_img(self, _buildenv, target, builddir, loop_dev):
        part_nr = self.node.et.attrib['part']
        imgname = os.path.join(builddir, self.node.et.text)

        do(['dd', f'if={loop_dev}p{part_nr}', f'of={imgname}'])

        target.images.append(self.node.et.text)
        target.image_packers[self.node.et.text] = default_packer


@FinetuningAction.register('copy_from_partition')
class CopyFromPartition(ImageFinetuningAction):

    def execute(self, _buildenv, _target):
        raise NotImplementedError('<copy_from_partition> may only be '
                                  'used in <losetup>')

    def execute_img(self, _buildenv, target, builddir, loop_dev):
        part_nr = self.node.et.attrib['part']
        aname = self.node.et.attrib['artifact']

        img_mnt = os.path.join(builddir, 'imagemnt')
        device = f'{loop_dev}p{part_nr}'

        with mount(device, img_mnt):
            mnt_fs = Filesystem(img_mnt)
            fname = mnt_fs.glob(self.node.et.text)

            if not fname:
                logging.error('No file matching "%s" found',
                              self.node.et.text)
                raise FinetuningException('No File found')

            if len(fname) > 1:
                logging.info('Pattern "%s" matches %d files',
                             self.node.et.text, len(fname))
                raise FinetuningException('Patter matches too many files')

            do(['cp', '-av', fname[0], os.path.join(builddir, aname)])

            target.images.append(aname)


@FinetuningAction.register('copy_to_partition')
class CopyToPartition(ImageFinetuningAction):

    def execute(self, _buildenv, _target):
        raise NotImplementedError('<copy_to_partition> may only be '
                                  'used in <losetup>')

    def execute_img(self, _buildenv, _target, builddir, loop_dev):
        part_nr = self.node.et.attrib['part']
        aname = self.node.et.attrib['artifact']

        img_mnt = os.path.join(builddir, 'imagemnt')
        device = f'{loop_dev}p{part_nr}'

        with mount(device, img_mnt):
            mnt_fs = Filesystem(img_mnt)
            fname = mnt_fs.fname(self.node.et.text)
            do(['cp', '-av', os.path.join(builddir, aname), fname])


@FinetuningAction.register('set_partition_type')
class SetPartitionTypeAction(ImageFinetuningAction):

    def execute(self, _buildenv, _target):
        raise NotImplementedError('<set_partition_type> may only be '
                                  'used in <losetup>')

    def execute_img(self, _buildenv, _target, _builddir, loop_dev):
        part_nr = self.node.et.attrib['part']
        part_type = self.node.et.attrib['type']

        do(['sfdisk', '--lock', '--part-type', loop_dev, part_nr, part_type])


@FinetuningAction.register('rm_apt_source')
class RmAptSource(FinetuningAction):

    def execute(self, buildenv, _target):

        src_path = f'{buildenv.path}/../target/etc/apt/sources.list'

        with open(src_path, 'r') as f:
            src_lst = f.read().split('\n')

        rm_src = self.node.et.text.replace('LOCALMACHINE', '10.0.2.2')
        src_lst = [src for src in src_lst if rm_src not in src]

        with open(src_path, 'w') as f:
            f.write('\n'.join(src_lst))


def do_finetuning(xml, buildenv, target):

    if not xml.has('target/finetuning'):
        return

    for i in xml.node('target/finetuning'):
        try:
            action = FinetuningAction(i)
            action.execute(buildenv, target)
        except KeyError:
            logging.exception("Unimplemented finetuning action '%s'",
                              i.et.tag)
            raise
        except subprocess.CalledProcessError as e:
            logging.exception('Finetuning Error: %s', e)
            raise
        except FinetuningException as e:
            logging.exception('Finetuning Error: %s', e)
            raise


def do_prj_finetuning(xml, buildenv, target, builddir):

    if not xml.has('target/project-finetuning'):
        return

    for i in xml.node('target/project-finetuning'):
        try:
            action = FinetuningAction(i)
            action.execute_prj(buildenv, target, builddir)
        except KeyError:
            logging.exception("Unimplemented Project Finetuning action '%s'",
                              i.et.tag)
        except subprocess.CalledProcessError as e:
            logging.exception('Project Finetuning Error: %s', e)
            raise
        except FinetuningException as e:
            logging.exception('Project Finetuning Error: %s', e)
            raise
        except Exception as e:
            logging.exception(str(e))
            raise
