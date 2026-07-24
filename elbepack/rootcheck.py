# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Linutronix GmbH

import logging
import os
import subprocess
import tempfile
import textwrap

from elbepack.cli import CliError
from elbepack.finetuning import LosetupAction
from elbepack.imgutils import losetup
from elbepack.treeutils import etree


def _loop_mount_reasons(xml):
    reasons = []

    for grub in xml.all('target/images/*/grub-install'):
        hd = grub.get_parent()
        reasons.append(
            f"<{hd.tag}> image '{hd.text('name')}' uses <grub-install>, which "
            'loop-mounts the disk image to run grub-install in a chroot')

    for bylabel in xml.all('target/fstab/bylabel'):
        if (bylabel.has('fs/fs-finetuning/device-command')
                or bylabel.has('fs/fs-finetuning/path-command')):
            reasons.append(
                f"filesystem '{bylabel.text('label')}' uses <fs-finetuning> "
                '(or the deprecated <tune2fs>) with a device-command/'
                'path-command, which loop-mounts that partition image')

    for ls in xml.all('target/project-finetuning/losetup'):
        if any(child.tag in LosetupAction.needs_loop_device for child in ls):
            reasons.append(
                f"<losetup img=\"{ls.et.attrib['img']}\"> contains an action "
                'that needs a loop device')

    return reasons


def _mknod_reasons(xml):
    reasons = []

    for node in xml.all('target/finetuning/mknod'):
        reasons.append(
            f"<mknod opts=\"{node.et.attrib.get('opts', '')}\">{node.et.text}</mknod> "
            'creates a device node, which needs to run rootful (real root / '
            'CAP_MKNOD, and in a container without a remapped user namespace)')

    return reasons


def xml_needs_rootful(xml):
    return _loop_mount_reasons(xml) + _mknod_reasons(xml)


def loop_mount_available():
    with tempfile.NamedTemporaryFile(prefix='elbe-loopcheck-') as f:
        f.truncate(1024 * 1024)
        try:
            with losetup(f.name):
                pass
        except subprocess.CalledProcessError as e:
            logging.debug('loop-mount preflight probe failed: %s', e)
            return False
    return True


def check_rootful_requirements(xmlfile):
    xml = etree(xmlfile)
    loop_reasons = _loop_mount_reasons(xml)
    mknod_reasons = _mknod_reasons(xml)

    problems = []
    if loop_reasons and not loop_mount_available():
        problems.append((
            'Linux loop devices, but this process is not able to create '
            'them (e.g. no access to /dev/loop-control)', loop_reasons))
    if mknod_reasons and os.geteuid() != 0:
        problems.append((
            'to create device nodes (mknod), but this process is not '
            'running as root', mknod_reasons))

    if not problems:
        return

    body = '\n\n'.join(
        f'This build needs {desc}:\n' + '\n'.join(f'  - {r}' for r in reasons)
        for desc, reasons in problems)

    raise CliError(message=textwrap.dedent(f"""
        {body}

        See the documentation for the elbe build command how to
        run a container with the necessary privileges.
        """))
