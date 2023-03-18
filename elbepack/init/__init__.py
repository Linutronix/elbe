# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2014-2015, 2017, 2018, 2024 Linutronix GmbH

import importlib.resources
import os
import pathlib
import shutil
import subprocess

import elbepack.init
from elbepack.debinstaller import NoKinitrdException, copy_kinitrd
from elbepack.shellhelper import do
from elbepack.templates import get_initvm_preseed, write_template
from elbepack.treeutils import etree
from elbepack.validate import validate_xml
from elbepack.version import is_devel
from elbepack.xmldefaults import ElbeDefaults


def create_initvm(name, xmlfile, directory, *,
                  sshport, soapport,
                  buildtype=None, skip_validation=False, cdrom=None, fail_on_warning=False,
                  build_bin=True, build_sources=True):
    if not skip_validation:
        validation = validate_xml(xmlfile)
        if validation:
            raise ValueError(validation)

    xml = etree(xmlfile)

    if not xml.has('initvm'):
        raise ValueError("xml missing mandatory section 'initvm'")

    if buildtype:
        pass
    elif xml.has('initvm/buildtype'):
        buildtype = xml.text('/initvm/buildtype')
    else:
        buildtype = 'nodefaults'

    defs = ElbeDefaults(buildtype)

    http_proxy = xml.text('/initvm/mirror/primary_proxy', default='')
    http_proxy = http_proxy.strip().replace('LOCALMACHINE', 'localhost')

    if cdrom:
        mirror = xml.node('initvm/mirror')
        mirror.clear()
        cdrom_elem = mirror.ensure_child('cdrom')
        cdrom_elem.set_text(os.path.abspath(cdrom))

    out_path = os.path.join(directory, '.elbe-in')
    os.makedirs(out_path)

    initvm_http_proxy = http_proxy.replace('http://localhost:',
                                           'http://10.0.2.2:')
    elbe_exe = '/usr/bin/elbe'
    if is_devel:
        elbe_exe = '/var/cache/elbe/devel/elbe'
    prj = xml.node('/initvm')

    d = {
         'is_devel': is_devel,
         'defs': defs,
         'directory': directory,
         'fail_on_warning': fail_on_warning,
         'initvm_domain': name,
         'xml': xml,
         'prj': prj,
         'http_proxy': initvm_http_proxy,
         'pkgs': xml.node('/initvm/pkg-list') or [],
         'preseed': get_initvm_preseed(xml),
         'soapport': soapport,
         'sshport': sshport,
    }

    if http_proxy != '':
        os.putenv('http_proxy', http_proxy)
        os.putenv('https_proxy', http_proxy)
        os.putenv('no_proxy', 'localhost,127.0.0.1')

    try:
        copy_kinitrd(xml.node('/initvm'), out_path)
    except NoKinitrdException as e:
        msg = (
            'Failure to download kernel/initrd debian Package\n'
            'Check Mirror configuration'
        )
        if 'SHA256SUMS' in str(e):
            msg += ('\nIf you use debmirror please read '
                    'https://github.com/Linutronix/elbe/issues/188 '
                    'on how to work around the issue')
        raise ValueError(msg) from e

    templates = [
        ('init-elbe.sh.mako', out_path, True, False),
        ('preseed.cfg.mako', out_path, True, False),
        ('Makefile.mako', directory, False, True),
        ('libvirt.xml.mako', directory, False, True),
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

    shutil.copyfile(xmlfile,
                    os.path.join(out_path, 'source.xml'))

    keys = []
    if xml.has('initvm/mirror/primary_key'):
        keys.append(xml.text('initvm/mirror/primary_key'))
    for key in xml.all('.//initvm/mirror/url-list/url/raw-key'):
        keys.append(key.et.text)

    if cdrom:
        keys.append(subprocess.run([
            '7z', 'x', '-so', cdrom, 'repo.pub',
        ], check=True, capture_output=True, encoding='utf-8').stdout)

    import_keyring = os.path.join(out_path, 'elbe-keyring')

    do(f'gpg --no-options \
             --no-default-keyring \
             --no-autostart \
             --keyring {import_keyring} --import',
       input=''.join(keys).encode('ascii'),
       check=False,
       env_add={'GNUPGHOME': out_path})

    export_keyring = import_keyring + '.gpg'

    do(f'gpg --no-options \
            --no-default-keyring \
            --no-autostart \
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

    if not build_bin:
        buildrepo_opts += '--skip-build-bin '

    if not build_sources:
        buildrepo_opts += '--skip-build-source '

    cdrom_opts = ''
    if prj.has('mirror/cdrom'):
        cdrom_opts = '--cdrom-device /dev/sr0 --cdrom-mount-path /media/cdrom0'

    with open(elbe_in / 'initrd-tree/usr/lib/finish-install.d/93initvm-repo',
              mode='x', opener=create_as_exec) as f:

        f.write(f'in-target {elbe_exe} '
                f'fetch_initvm_pkgs {buildrepo_opts} {cdrom_opts} /var/cache/elbe/source.xml')
