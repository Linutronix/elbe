# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Linutronix GmbH

import contextlib
import subprocess

import pytest

from elbepack.cli import CliError
from elbepack.rootcheck import (
    check_rootful_requirements,
    loop_mount_available,
    xml_needs_rootful,
)
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


def test_loop_mount_available_true(monkeypatch):
    @contextlib.contextmanager
    def fake_losetup(dev, extra_args=[]):
        yield '/dev/loop0'

    monkeypatch.setattr('elbepack.rootcheck.losetup', fake_losetup)
    assert loop_mount_available() is True


def test_loop_mount_available_false_on_called_process_error(monkeypatch):
    @contextlib.contextmanager
    def fake_losetup(dev, extra_args=[]):
        raise subprocess.CalledProcessError(1, ['losetup'])
        yield  # pragma: no cover

    monkeypatch.setattr('elbepack.rootcheck.losetup', fake_losetup)
    assert loop_mount_available() is False


def test_check_rootful_requirements_skips_probe_when_nothing_needed(tmp_path, monkeypatch):
    def fail(*a, **k):
        raise AssertionError('loop_mount_available should not be called')

    monkeypatch.setattr('elbepack.rootcheck.loop_mount_available', fail)
    xmlfile = tmp_path / 'x.xml'
    xmlfile.write_text('<xml><target/></xml>')
    check_rootful_requirements(str(xmlfile))


def test_check_rootful_requirements_passes_when_available(tmp_path, monkeypatch):
    monkeypatch.setattr('elbepack.rootcheck.loop_mount_available', lambda: True)
    xmlfile = tmp_path / 'x.xml'
    xmlfile.write_text("""
        <xml><target><images><msdoshd>
            <name>disk.img</name><grub-install></grub-install>
        </msdoshd></images></target></xml>
    """)
    check_rootful_requirements(str(xmlfile))


def test_check_rootful_requirements_raises_when_loop_unavailable(tmp_path, monkeypatch):
    monkeypatch.setattr('elbepack.rootcheck.loop_mount_available', lambda: False)
    xmlfile = tmp_path / 'x.xml'
    xmlfile.write_text("""
        <xml><target><images><msdoshd>
            <name>disk.img</name><grub-install></grub-install>
        </msdoshd></images></target></xml>
    """)
    with pytest.raises(CliError) as exc_info:
        check_rootful_requirements(str(xmlfile))
    assert 'grub-install' in str(exc_info.value)
    assert 'elbe build command' in str(exc_info.value)


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


def test_check_rootful_requirements_raises_when_mknod_and_not_root(tmp_path, monkeypatch):
    monkeypatch.setattr('elbepack.rootcheck.os.geteuid', lambda: 1000)
    xmlfile = tmp_path / 'x.xml'
    xmlfile.write_text("""
        <xml><target><finetuning>
            <mknod opts="c 5 0">/dev/tty</mknod>
        </finetuning></target></xml>
    """)
    with pytest.raises(CliError) as exc_info:
        check_rootful_requirements(str(xmlfile))
    assert 'mknod' in str(exc_info.value)


def test_check_rootful_requirements_passes_when_mknod_and_root(tmp_path, monkeypatch):
    monkeypatch.setattr('elbepack.rootcheck.os.geteuid', lambda: 0)
    xmlfile = tmp_path / 'x.xml'
    xmlfile.write_text("""
        <xml><target><finetuning>
            <mknod opts="c 5 0">/dev/tty</mknod>
        </finetuning></target></xml>
    """)
    check_rootful_requirements(str(xmlfile))


def test_check_rootful_requirements_combines_loop_and_mknod_problems(tmp_path, monkeypatch):
    monkeypatch.setattr('elbepack.rootcheck.loop_mount_available', lambda: False)
    monkeypatch.setattr('elbepack.rootcheck.os.geteuid', lambda: 1000)
    xmlfile = tmp_path / 'x.xml'
    xmlfile.write_text("""
        <xml><target>
            <images><msdoshd>
                <name>disk.img</name><grub-install></grub-install>
            </msdoshd></images>
            <finetuning>
                <mknod opts="c 5 0">/dev/tty</mknod>
            </finetuning>
        </target></xml>
    """)
    with pytest.raises(CliError) as exc_info:
        check_rootful_requirements(str(xmlfile))
    assert 'grub-install' in str(exc_info.value)
    assert 'mknod' in str(exc_info.value)
