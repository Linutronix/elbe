# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2014-2015, 2017, 2018 Linutronix GmbH

import importlib.resources
import logging
import os
import pathlib
import shutil
import subprocess
import sys
from optparse import OptionParser

import elbepack.init
from elbepack.config import cfg
from elbepack.debinstaller import NoKinitrdException, copy_kinitrd
from elbepack.log import elbe_logging
from elbepack.shellhelper import do
from elbepack.templates import get_initvm_preseed, write_template
from elbepack.treeutils import etree
from elbepack.validate import validate_xml
from elbepack.version import elbe_version, is_devel
from elbepack.xmldefaults import ElbeDefaults


def run_command(argv):

    oparser = OptionParser(usage='usage: %prog init [options] <filename>')

    oparser.add_option('--skip-validation', action='store_true',
                       dest='skip_validation', default=False,
                       help='Skip xml schema validation')

    oparser.add_option('--directory', dest='directory', default='./build',
                       help='Working directory (default is build)',
                       metavar='FILE')

    oparser.add_option(
        '--cdrom',
        dest='cdrom',
        help='Use FILE as cdrom iso, and use that to build the initvm',
        metavar='FILE')

    oparser.add_option('--buildtype', dest='buildtype',
                       help='Override the buildtype')

    oparser.add_option(
        '--debug',
        dest='debug',
        action='store_true',
        default=False,
        help='start qemu in graphical mode to enable console switch')

    oparser.add_option(
        '--skip-build-bin',
        action='store_false',
        dest='build_bin',
        default=True,
        help='Skip building Binary Repository CDROM, for exact Reproduction')

    oparser.add_option(
        '--skip-build-sources',
        action='store_false',
        dest='build_sources',
        default=True,
        help='Skip building Source CDROM')

    (opt, args) = oparser.parse_args(argv)

    if not args:
        print('no filename specified')
        oparser.print_help()
        sys.exit(78)
    elif len(args) > 1:
        print('too many filenames specified')
        oparser.print_help()
        sys.exit(79)

    with elbe_logging({'files': None}):
        if not opt.skip_validation:
            validation = validate_xml(args[0])
            if validation:
                logging.error('xml validation failed. Bailing out')
                for i in validation:
                    logging.error(i)
                sys.exit(81)

        xml = etree(args[0])

        if not xml.has('initvm'):
            logging.error('fatal error: '
                          "xml missing mandatory section 'initvm'")
            sys.exit(82)

        if opt.buildtype:
            buildtype = opt.buildtype
        elif xml.has('initvm/buildtype'):
            buildtype = xml.text('/initvm/buildtype')
        else:
            buildtype = 'nodefaults'

        defs = ElbeDefaults(buildtype)

        http_proxy = xml.text('/initvm/mirror/primary_proxy', default='')
        http_proxy = http_proxy.strip().replace('LOCALMACHINE', 'localhost')

        if opt.cdrom:
            mirror = xml.node('initvm/mirror')
            mirror.clear()
            cdrom = mirror.ensure_child('cdrom')
            cdrom.set_text(os.path.abspath(opt.cdrom))

        try:
            os.makedirs(opt.directory)
        except OSError as e:
            logging.error('unable to create project directory: %s (%s)',
                          opt.directory,
                          e.strerror)
            sys.exit(83)

        out_path = os.path.join(opt.directory, '.elbe-in')
        try:
            os.makedirs(out_path)
        except OSError as e:
            logging.error('unable to create subdirectory: %s (%s)',
                          out_path,
                          e.strerror)
            sys.exit(84)

        initvm_http_proxy = http_proxy.replace('http://localhost:',
                                               'http://10.0.2.2:')
        elbe_exe = '/usr/bin/elbe'
        if is_devel:
            elbe_exe = '/var/cache/elbe/devel/elbe'
        prj = xml.node('/initvm')

        d = {'elbe_exe': elbe_exe,
             'elbe_version': elbe_version,
             'is_devel': is_devel,
             'defs': defs,
             'opt': opt,
             'xml': xml,
             'prj': prj,
             'http_proxy': initvm_http_proxy,
             'pkgs': xml.node('/initvm/pkg-list') or [],
             'preseed': get_initvm_preseed(xml),
             'cfg': cfg}

        if http_proxy != '':
            os.putenv('http_proxy', http_proxy)
            os.putenv('https_proxy', http_proxy)
            os.putenv('no_proxy', 'localhost,127.0.0.1')

        try:
            copy_kinitrd(xml.node('/initvm'), out_path)
        except NoKinitrdException as e:
            msg = str(e)
            logging.error('Failure to download kernel/initrd debian Package:')
            logging.error('')
            logging.error(msg)
            logging.error('')
            logging.error('Check Mirror configuration')
            if 'SHA256SUMS' in msg:
                logging.error('If you use debmirror please read '
                              'https://github.com/Linutronix/elbe/issues/188 '
                              'on how to work around the issue')
            sys.exit(85)

        templates = [
            ('init-elbe.sh.mako', out_path, True, False),
            ('preseed.cfg.mako', out_path, True, False),
            ('Makefile.mako', opt.directory, False, True),
            ('libvirt.xml.mako', opt.directory, False, True),
            ('apt.conf.mako', out_path, False, False),
            ('default-init.xml', out_path, False, False),
        ]

        template_dir = importlib.resources.files(elbepack.init)

        for t, out_dir, make_executable, linebreak in templates:
            o = t.replace('.mako', '')

            with importlib.resources.as_file(template_dir / t) as template:
                write_template(
                    os.path.join(out_dir, o),
                    template, d, linebreak=linebreak,
                )

            if make_executable:
                os.chmod(os.path.join(out_dir, o), 0o755)

        shutil.copyfile(args[0],
                        os.path.join(out_path, 'source.xml'))

        keys = []
        for key in xml.all('.//initvm/mirror/url-list/url/raw-key'):
            keys.append(key.et.text)

        if opt.cdrom:
            keys.append(subprocess.run([
                '7z', 'x', '-so', opt.cdrom, 'repo.pub',
            ], check=True, capture_output=True, encoding='utf-8').stdout)

        import_keyring = os.path.join(out_path, 'elbe-keyring')

        do(f'gpg --no-options \
                 --no-default-keyring \
                 --keyring {import_keyring} --import',
           stdin=''.join(keys).encode('ascii'),
           allow_fail=True,
           env_add={'GNUPGHOME': out_path})

        export_keyring = import_keyring + '.gpg'

        do(f'gpg --no-options \
                --no-default-keyring \
                --keyring {import_keyring} \
                --export \
                --output {export_keyring}',
            env_add={'GNUPGHOME': out_path})

        if is_devel:
            opts = [
                '--exclude-vcs',
                '--exclude-vcs-ignores',
            ]

            tar_fname = os.path.join(out_path, 'elbe-devel.tar.bz2')
            source_dir = pathlib.Path(__file__).parents[2]
            subprocess.run([
                'tar', 'cfj', tar_fname, *opts, '-C', source_dir, 'elbepack', 'elbe'
            ], check=True)

        to_cpy = [('apt.conf', 'etc/apt'),
                  ('init-elbe.sh', ''),
                  ('source.xml', ''),
                  ('initrd-cdrom.gz', ''),
                  ('vmlinuz', ''),
                  ('preseed.cfg', '')]

        elbe_in = pathlib.Path(out_path)

        if is_devel:
            to_cpy.append(('elbe-devel.tar.bz2', ''))

        # Convert relative rfs path to absolute in the system
        to_cpy = [(elbe_in / src, elbe_in / 'initrd-tree' / dst)
                  for src, dst
                  in to_cpy]

        # These are already absolute path!
        keyrings = elbe_in / 'initrd-tree' / 'usr/share/keyrings'
        for gpg in elbe_in.glob('*.gpg'):
            to_cpy.append((gpg, keyrings))

        for src, dst in to_cpy:
            try:
                os.makedirs(dst)
            except FileExistsError:
                pass
            shutil.copy(src, dst)

        elbe_in.joinpath('initrd-tree/usr/lib/finish-install.d').mkdir(parents=True, exist_ok=True)

        def create_as_exec(file, flags):
            return os.open(file, flags, mode=0o755)

        buildrepo_opts = ''

        if not opt.build_bin:
            buildrepo_opts += '--skip-build-bin '

        if not opt.build_sources:
            buildrepo_opts += '--skip-build-source '

        cdrom_opts = ''
        if prj.has('mirror/cdrom'):
            cdrom_opts = '--cdrom-device /dev/sr0 --cdrom-mount-path /media/cdrom0'

        with open(elbe_in / 'initrd-tree/usr/lib/finish-install.d/93initvm-repo',
                  mode='x', opener=create_as_exec) as f:

            f.write(f'in-target {elbe_exe} '
                    f'fetch_initvm_pkgs {buildrepo_opts} {cdrom_opts} /var/cache/elbe/source.xml')
