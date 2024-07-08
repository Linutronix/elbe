# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2013-2017 Linutronix GmbH

import argparse
import os

import apt

import apt_pkg

from elbepack.elbexml import ElbeXML, ValidationMode


def run_command(argv):

    aparser = argparse.ArgumentParser(prog='elbe pkgdiff')
    aparser.add_argument(
        '--noauto',
        action='store_true',
        dest='noauto',
        default=False,
        help='Dont compare automatically installed Packages')
    aparser.add_argument('rfs1')
    aparser.add_argument('rfs2')
    args = aparser.parse_args(argv)

    gen_rfs = args.rfs1
    fix_rfs = args.rfs2

    x = os.path.join(gen_rfs, 'etc/elbe_base.xml')
    xml = ElbeXML(
        x,
        skip_validate=True,
        url_validation=ValidationMode.NO_CHECK)
    arch = xml.text('project/arch', key='arch')

    apt_pkg.init_config()
    apt_pkg.config.set('RootDir', gen_rfs)
    apt_pkg.config.set('APT::Architecture', arch)
    apt_pkg.init_system()
    gen_cache = apt_pkg.Cache(apt.progress.base.OpProgress())
    gc = apt.Cache()

    gen_pkgs = {}
    for p in gen_cache.packages:
        if args.noauto:
            if p.current_ver and not \
               gc[p.name].is_auto_installed and not \
               p.essential:
                gen_pkgs[p.name] = p.current_ver
        else:
            if p.current_ver and not p.essential:
                gen_pkgs[p.name] = p.current_ver

    apt_pkg.init_config()
    apt_pkg.config.set('RootDir', fix_rfs)
    apt_pkg.config.set('APT::Architecture', arch)
    apt_pkg.init_system()
    fix_cache = apt_pkg.Cache(apt.progress.base.OpProgress())
    fc = apt.Cache()

    fix_pkgs = {}
    for p in fix_cache.packages:
        if args.noauto:
            if p.current_ver and not \
               fc[p.name].is_auto_installed and not \
               p.essential:
                fix_pkgs[p.name] = p.current_ver
        else:
            if p.current_ver and not p.essential:
                fix_pkgs[p.name] = p.current_ver

    for p in fix_pkgs:
        if p not in gen_pkgs:
            print(f'+<pkg>{p}</pkg>')

    for p in gen_pkgs:
        if p not in fix_pkgs.keys():
            print(f'-<pkg>{p}</pkg>')

    for p in fix_pkgs:
        if p in gen_pkgs.keys() and fix_pkgs[p] != gen_pkgs[p]:
            print(f'{p}: Version mismatch {fix_pkgs[p]} != {gen_pkgs[p]}')
