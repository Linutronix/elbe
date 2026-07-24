# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Linutronix GmbH

import pytest

from elbepack.rootcheck import xml_needs_rootful
from elbepack.treeutils import etree


def _xml(s):
    return etree(None, string=s)


def test_needs_no_rootful_for_plain_xml():
    assert xml_needs_rootful(_xml('<xml><target/></xml>')) == []


@pytest.mark.parametrize('hd_tag', ['msdoshd', 'gpthd'])
def test_needs_rootful_for_grub_install(hd_tag):
    xml = _xml(f"""
        <xml><target><images><{hd_tag}>
            <name>disk.img</name>
            <grub-install></grub-install>
        </{hd_tag}></images></target></xml>
    """)
    reasons = xml_needs_rootful(xml)
    assert len(reasons) == 1
    assert 'grub-install' in reasons[0]


@pytest.mark.parametrize('command_tag', ['device-command', 'path-command'])
def test_needs_rootful_for_fs_finetuning(command_tag):
    xml = _xml(f"""
        <xml><target><fstab><bylabel>
            <label>rootfs</label>
            <fs>
                <type>ext4</type>
                <fs-finetuning><{command_tag}>echo hi</{command_tag}></fs-finetuning>
            </fs>
        </bylabel></fstab></target></xml>
    """)
    reasons = xml_needs_rootful(xml)
    assert len(reasons) == 1
    assert 'rootfs' in reasons[0]


def test_needs_rootful_for_tune2fs():
    xml = _xml("""
        <xml><target><fstab><bylabel>
            <label>rootfs</label>
            <fs>
                <type>ext4</type>
                <tune2fs>-i 0</tune2fs>
            </fs>
        </bylabel></fstab></target></xml>
    """)
    reasons = xml_needs_rootful(xml)
    assert len(reasons) == 1
    assert 'rootfs' in reasons[0]
    assert 'tune2fs' in reasons[0]


def test_needs_rootful_for_cdrom_mirror_in_xml():
    xml = _xml('<xml><project><mirror><cdrom>/some.iso</cdrom></mirror></project></xml>')
    reasons = xml_needs_rootful(xml)
    assert len(reasons) == 1
    assert 'loop-mounted' in reasons[0]


def test_needs_rootful_for_cdrom_param_even_when_not_in_xml():
    xml = _xml('<xml><target/></xml>')
    reasons = xml_needs_rootful(xml, cdrom='/some.iso')
    assert len(reasons) == 1
    assert 'loop-mounted' in reasons[0]


def test_needs_no_rootful_for_fs_finetuning_file_command():
    xml = _xml("""
        <xml><target><fstab><bylabel>
            <label>rootfs</label>
            <fs>
                <type>ext4</type>
                <fs-finetuning><file-command>echo hi</file-command></fs-finetuning>
            </fs>
        </bylabel></fstab></target></xml>
    """)
    assert xml_needs_rootful(xml) == []


@pytest.mark.parametrize('child_xml', [
    '<copy_from_partition part="1" artifact="a">out.bin</copy_from_partition>',
    '<copy_to_partition part="1" artifact="a">in.bin</copy_to_partition>',
    '<command part="1">true</command>',
])
def test_needs_rootful_for_specific_losetups(child_xml):
    xml = _xml(f"""
        <xml><target><project-finetuning>
            <losetup img="disk.img">{child_xml}</losetup>
        </project-finetuning></target></xml>
    """)
    assert len(xml_needs_rootful(xml)) == 1


def test_needs_no_rootful_for_some_losetups():
    xml = _xml("""
        <xml><target><project-finetuning>
            <losetup img="disk.img">
                <extract_partition part="1">out.img</extract_partition>
                <set_partition_type part="2">83</set_partition_type>
                <insert_partition part="3">in.img</insert_partition>
            </losetup>
        </project-finetuning></target></xml>
    """)
    assert xml_needs_rootful(xml) == []


def test_needs_rootful_detects_mknod():
    xml = _xml("""
        <xml><target><finetuning>
            <mknod opts="c 5 0">/dev/tty</mknod>
        </finetuning></target></xml>
    """)
    reasons = xml_needs_rootful(xml)
    assert len(reasons) == 1
    assert 'mknod' in reasons[0]
    assert '/dev/tty' in reasons[0]
