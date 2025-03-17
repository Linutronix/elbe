# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2025 Linutronix GmbH

import os
import warnings

import pytest

# Work around swig bug affecting python gpgme
# https://github.com/swig/swig/issues/3061
with warnings.catch_warnings():
    warnings.simplefilter('ignore')
    import gpg  # noqa: F401

import elbepack.filesystem
import elbepack.finetuning
import elbepack.treeutils


def requires_root(f):
    return pytest.mark.skipif(os.geteuid() != 0, reason='requires execution as root')(f)


@pytest.fixture
def target(tmpdir):
    return elbepack.filesystem.Filesystem(tmpdir)


def finetune(target, xml):
    node = elbepack.treeutils.etree(None, string=xml).root
    action = elbepack.finetuning._action_for_node(node)
    action.execute(None, target)


def test_rm(target):
    assert not target.exists('foo')

    finetune(target, '<rm>foo</rm>')
    assert not target.exists('foo')

    target.touch_file('foo')
    assert target.exists('foo')

    finetune(target, '<rm>foo</rm>')
    assert not target.exists('foo')


def test_mkdir(target):
    finetune(target, '<mkdir>foo</mkdir>')
    assert target.isdir('foo')

    finetune(target, '<mkdir>foo</mkdir>')
    assert target.isdir('foo')


@requires_root
def test_mknod(target):
    finetune(target, '<mknod opts="c 5 0">foo</mknod>')
    assert target.exists('foo')


def test_cp(target):
    target.touch_file('foo')

    finetune(target, '<cp path="foo">bar</cp>')
    assert target.exists('bar')

    finetune(target, '<cp path="foo">bar</cp>')
    assert target.exists('bar')


def test_mv(target):
    target.touch_file('foo')

    finetune(target, '<mv path="foo">bar</mv>')
    assert not target.exists('foo')
    assert target.exists('bar')


@requires_root
def test_ln(target):
    root = elbepack.filesystem.Filesystem('/')
    target.touch_file('foo')

    finetune(root, '<ln path="foo">{}</ln>'.format(
        target.fname('bar'),
    ))
    assert target.exists('foo')
    assert target.islink('bar')
    assert target.readlink('bar') == 'foo'


def test_file_plain(target):
    finetune(target, """
    <file encoding="plain" dst="foo">bar</file>
    """)
    assert target.read_file('foo') == 'bar'

    finetune(target, """
<file encoding="plain" dst="foo">
    bar
</file>
    """)
    assert target.read_file('foo') == 'bar'

    finetune(target, """
<file encoding="plain" dst="foo">

    baz

</file>
    """)
    assert target.read_file('foo') == '\nbaz\n'


def test_file_raw(target):
    finetune(target, """
    <file encoding="raw" dst="foo">
bar
    </file>
    """)
    assert target.read_file('foo') == 'bar'

    finetune(target, """
    <file encoding="raw" dst="foo">

baz

    </file>
    """)
    assert target.read_file('foo') == '\nbaz\n'

    # This is probably unintentional
    finetune(target, """
    <file encoding="raw" dst="foo">foo
baz
    </file>
    """)
    assert target.read_file('foo') == 'baz'


def test_file_base64(target):
    finetune(target, """
    <file encoding="base64" dst="foo">YmFyCg==</file>
    """)
    assert target.read_file('foo') == 'bar\n'

    finetune(target, """
    <file encoding="base64" dst="foo">
         YmFyCg==
    </file>
    """)
    assert target.read_file('foo') == 'bar\n'


def test_file_append(target):
    finetune(target, """
    <file encoding="plain" dst="foo">bar</file>
    """)
    assert target.read_file('foo') == 'bar'

    finetune(target, """
    <file encoding="plain" dst="foo" append="true">baz</file>
    """)
    assert target.read_file('foo') == 'barbaz'
