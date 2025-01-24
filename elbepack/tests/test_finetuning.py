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
    target.touch_file('foo')

    finetune(target, '<ln path="foo">bar</ln>')
    assert target.exists('foo')
    assert target.islink('bar')
    assert target.readlink('bar') == 'foo'
