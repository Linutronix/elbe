# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2015-2017 Linutronix GmbH

import os
import pathlib
from tempfile import NamedTemporaryFile
from urllib.request import urlopen

from elbepack.egpg import unarmor_openpgp_keyring
from elbepack.treeutils import strip_leading_whitespace_from_lines


def _write_env(fp, k, v):
    fp.write(f'{k}="{v}"\n')


def pbuilder_write_config(builddir, xml, noccache):
    distname = xml.prj.text('suite')
    pbuilderrc_fname = os.path.join(builddir, 'pbuilderrc')
    fp = open(pbuilderrc_fname, 'w')

    fp.write('#!/bin/sh\n')
    fp.write('set -e\n')
    _write_env(fp, 'MIRRORSITE', xml.get_primary_mirror(False))
    _write_env(fp, 'OTHERMIRROR', f'deb http://127.0.0.1:7588/repo{builddir}/repo {distname} main')
    _write_env(fp, 'BASETGZ', os.path.join(builddir, 'pbuilder', 'base.tgz'))
    _write_env(fp, 'DISTRIBUTION', distname)
    _write_env(fp, 'BUILDRESULT', os.path.join(builddir, 'pbuilder', 'result'))
    _write_env(fp, 'APTCACHE', os.path.join(builddir, 'pbuilder', 'aptcache'))
    _write_env(fp, 'HOOKDIR', os.path.join(builddir, 'pbuilder', 'hooks.d'))
    _write_env(fp, 'PATH', '/usr/share/elbe/qemu-elbe:$PATH')

    if xml.text('project/arch', key='arch') != 'amd64':
        _write_env(fp, 'ARCHITECTURE', xml.text('project/buildimage/arch', key='arch'))
        _write_env(fp, 'DEBOOTSTRAP', 'qemu-debootstrap')
        fp.write('DEBOOTSTRAPOPTS=("${DEBOOTSTRAPOPTS[@]}" "--arch=$ARCHITECTURE")\n')

    if xml.prj.has('noauth'):
        fp.write('DEBOOTSTRAPOPTS=("${DEBOOTSTRAPOPTS[@]}" "--no-check-gpg")\n')
        fp.write('for i in "${!DEBOOTSTRAPOPTS[@]}"; do '
                 'if [[ ${DEBOOTSTRAPOPTS[i]} == "--force-check-gpg" ]]; then '
                 "unset 'DEBOOTSTRAPOPTS[i]'; break; "
                 'fi done\n')
        fp.write('export ALLOWUNTRUSTED="yes"\n')

    # aptitude segfaults with armhf changeroots, great! :)
    # link: https://bugs.debian.org/cgi-bin/bugreport.cgi?bug=834990
    _write_env(fp, 'PBUILDERSATISFYDEPENDSCMD',
               '/usr/lib/pbuilder/pbuilder-satisfydepends-experimental')

    if not noccache:
        fp.write(f'export CCACHE_DIR="{builddir}/ccache"\n')
        fp.write('export PATH="/usr/lib/ccache:${PATH}"\n')
        fp.write('EXTRAPACKAGES=ccache\n')
        fp.write(f'export CCACHE_CONFIGPATH="{builddir}/ccache/ccache.conf"\n')
        fp.write('BINDMOUNTS="${CCACHE_DIR}"')
    fp.close()


def pbuilder_write_cross_config(builddir, xml, noccache):
    distname = xml.prj.text('suite')
    pbuilderrc_fname = os.path.join(builddir, 'cross_pbuilderrc')
    fp = open(pbuilderrc_fname, 'w')

    fp.write('#!/bin/sh\n')
    fp.write('set -e\n')
    _write_env(fp, 'MIRRORSITE', xml.get_primary_mirror(False, hostsysroot=True))
    _write_env(fp, 'OTHERMIRROR', f'deb http://127.0.0.1:7588/repo{builddir}/repo {distname} main')
    _write_env(fp, 'BASETGZ', os.path.join(builddir, 'pbuilder_cross', 'base.tgz'))
    _write_env(fp, 'DISTRIBUTION', distname)
    _write_env(fp, 'BUILDRESULT', os.path.join(builddir, 'pbuilder_cross', 'result'))
    _write_env(fp, 'APTCACHE', os.path.join(builddir, 'pbuilder_cross', 'aptcache'))
    _write_env(fp, 'HOOKDIR', os.path.join(builddir, 'pbuilder_cross', 'hooks.d'))
    _write_env(fp, 'PBUILDERSATISFYDEPENDSCMD',
               '/usr/lib/pbuilder/pbuilder-satisfydepends-apt')

    if xml.prj.has('noauth'):
        fp.write(
            'DEBOOTSTRAPOPTS=("${DEBOOTSTRAPOPTS[@]}" "--no-check-gpg")\n')
        fp.write('for i in "${!DEBOOTSTRAPOPTS[@]}"; do '
                 'if [[ ${DEBOOTSTRAPOPTS[i]} == "--force-check-gpg" ]]; then '
                 "unset 'DEBOOTSTRAPOPTS[i]'; break; "
                 'fi done\n')
        fp.write('export ALLOWUNTRUSTED="yes"\n')

    if not noccache:
        fp.write(f'export CCACHE_DIR="{builddir}/ccache"\n')
        fp.write('export PATH="/usr/lib/ccache:${PATH}"\n')
        fp.write('EXTRAPACKAGES=ccache\n')
        fp.write(f'export CCACHE_CONFIGPATH="{builddir}/ccache/ccache.conf"\n')
        fp.write('BINDMOUNTS="${CCACHE_DIR}"')
    fp.close()


def pbuilder_write_apt_conf(builddir, xml):

    # writing apt.conf is only necessary, when we have noauth
    # return when its not set
    if not xml.prj.has('noauth'):
        return

    # noauth is set
    # create pbuilder/aptconfdir/apt.conf.d/16allowuntrusted
    aptconf_dir = os.path.join(builddir, 'aptconfdir', 'apt.conf.d')
    fp = open(os.path.join(aptconf_dir, '16allowuntrusted'), 'w')

    # Make apt-get use --force-yes which is not specified by
    # pbuilder-satisfy-depends
    fp.write('APT::Get::force-yes "true";\n')

    # Also for safety add this:
    fp.write('APT::Get::AllowUnauthenticated "true";\n')

    # Force apt-secure to issue only warnings for the unsigned repositories
    fp.write('Acquire::AllowInsecureRepositories "true";\n')

    # Make aptitude install untrusted packages without asking
    fp.write('Aptitude::CmdLine::Ignore-Trust-Violations "true";\n')
    fp.close()


def mirror_script_add_key_url(key_url):
    key_url = key_url.replace('LOCALMACHINE', '10.0.2.2')
    key_conn = urlopen(key_url, None, 10)
    key_text = key_conn.read()
    key_conn.close()

    return key_text


def pbuilder_write_repo_hook(builddir, xml, cross):

    if cross:
        pbuilder_hook_dir = os.path.join(builddir, 'pbuilder_cross', 'hooks.d')
    else:
        pbuilder_hook_dir = os.path.join(builddir, 'pbuilder', 'hooks.d')

    with open(os.path.join(pbuilder_hook_dir, 'H10elbe_apt_update'), 'w') as f:
        f.write('#!/bin/sh\napt-get update\n')

    with open(os.path.join(pbuilder_hook_dir, 'G10elbe_apt_sources'), 'w') as f:

        mirrors = f"deb http://127.0.0.1:7588/repo{builddir}/repo {xml.prj.text('suite')} main\n"
        mirrors += xml.create_apt_sources_list(hostsysroot=False)
        if cross:
            mirrors += '\n' + xml.create_apt_sources_list(hostsysroot=True)

        keys = get_apt_keys(builddir, xml)

        f.write('#!/bin/sh\n')

        # cat reads from stdin (-) and redirect (>) to
        # /etc/apt/sources.list
        f.write(f'cat -> /etc/apt/sources.list <<EOF\n{mirrors}\nEOF\n')

        for name, key in keys:
            f.write(f'cat -> /etc/apt/trusted.gpg.d/{name}.asc <<EOF\n{key}\nEOF\n')

        f.write('apt-get update\n')


def get_debootstrap_key(xml):
    if xml.prj.has('mirror/primary_host') and xml.prj.has('mirror/primary_key'):
        m = xml.prj.node('mirror')

        if m.has('options'):
            options = '[%s]' % ' '.join([opt.et.text.strip(' \t\n')
                                         for opt
                                         in m.all('options/option')])
        else:
            options = ''

        if 'trusted=yes' not in options:
            return strip_leading_whitespace_from_lines(m.text('primary_key'))


def pbuilder_get_debootstrap_key_path(chrootpath, xml):
    # If we have a primary key for use with debootstrap, BuildEnv.debootstrap
    # will have added the key. We use the same key for the pbuilder
    # debootstrap options.
    key = get_debootstrap_key(xml)
    if key is None:
        return None

    tmp_file = NamedTemporaryFile(delete=False)

    tmp_file.write(unarmor_openpgp_keyring(key))
    tmp_file.close()

    return tmp_file.name


def get_apt_keys(builddir, xml):

    if xml.prj is None:
        return (['# No Project'], [])

    if not xml.prj.has('mirror') and not xml.prj.has('mirror/cdrom'):
        return (['# No mirrors configured'], [])

    keys = [('elbe-localrepo', pathlib.Path(builddir, 'repo', 'repo.pub').read_text())]

    debootstrap_key = get_debootstrap_key(xml)
    if debootstrap_key:
        keys.append(('elbe-xml-primary-key', debootstrap_key))

    if xml.prj.has('mirror/primary_host') and xml.prj.has('mirror/url-list'):

        for i, url in enumerate(xml.prj.node('mirror/url-list')):

            if url.has('options'):
                options = '[%s]' % ' '.join([opt.et.text.strip(' \t\n')
                                             for opt
                                             in url.all('options/option')])
            else:
                options = ''

            if 'trusted=yes' in options:
                continue

            if url.has('raw-key'):
                keys.append((f'elbe-xml-raw-key{i}',
                             strip_leading_whitespace_from_lines(url.text('raw-key'))))

    return keys
