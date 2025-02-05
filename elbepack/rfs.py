# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2014-2017 Linutronix GmbH
# SPDX-FileCopyrightText: 2014 Ferdinand Schwenk <ferdinand.schwenk@emtrion.de>

import logging
import os
import subprocess
from urllib.parse import urlsplit

from elbepack.efilesystem import ChRootFilesystem, dpkg_architecture
from elbepack.egpg import unarmor_openpgp_keyring
from elbepack.shellhelper import chroot, do
from elbepack.templates import get_preseed, preseed_to_text, write_pack_template
from elbepack.treeutils import strip_leading_whitespace_from_lines


def create_apt_prefs(xml, rfs):

    filename = 'etc/apt/preferences'

    if rfs.lexists(filename):
        rfs.remove(filename)

    rfs.mkdir_p('/etc/apt')

    pinned_origins = []
    if xml.has('project/mirror/url-list'):
        for url in xml.node('project/mirror/url-list'):
            if not url.has('binary'):
                continue

            repo = url.node('binary')
            if 'pin' not in repo.et.attrib:
                continue

            origin = urlsplit(repo.et.text.strip()).hostname
            pin = repo.et.attrib['pin']
            if 'package' in repo.et.attrib:
                package = repo.et.attrib['package']
            else:
                package = '*'
            pinning = {'pin': pin,
                       'origin': origin,
                       'package': package}
            pinned_origins.append(pinning)

    d = {'xml': xml,
         'prj': xml.node('/project'),
         'pkgs': xml.node('/target/pkg-list'),
         'porgs': pinned_origins}

    write_pack_template(rfs.fname(filename), 'preferences.mako', d)


class DebootstrapException (Exception):
    def __init__(self):
        super().__init__('Debootstrap Failed')


class BuildEnv:
    def __init__(self, xml, path, build_sources=False,
                 clean=False, arch='default', hostsysroot=False):

        self.xml = xml
        self.path = path
        self.rpcaptcache = None
        self.arch = arch
        self.hostsysroot = hostsysroot

        self.rfs = ChRootFilesystem(path, xml.defs['userinterpr'])

        if clean:
            self.rfs.rmtree('')

        # TODO think about reinitialization if elbe_version differs
        if not self.rfs.isfile('etc/elbe_version'):
            # avoid starting daemons inside the buildenv
            self.rfs.mkdir_p('usr/sbin')
            # grub-legacy postinst will fail if /boot/grub does not exist
            self.rfs.mkdir_p('boot/grub')
            self.rfs.write_file(
                'usr/sbin/policy-rc.d',
                0o755,
                '#!/bin/sh\nexit 101\n')
            self.debootstrap(arch)
            self.fresh_debootstrap = True
            self.need_dumpdebootstrap = True
        else:
            self.fresh_debootstrap = False
            self.need_dumpdebootstrap = False

        self.initialize_dirs(build_sources=build_sources)
        create_apt_prefs(self.xml, self.rfs)

    def cdrom_umount(self):
        if self.xml.prj.has('mirror/cdrom'):
            cdrompath = self.rfs.fname('cdrom')
            do(['umount', cdrompath])
            do(['rm', '-f', self.path + '/etc/apt/trusted.gpg.d/elbe-cdrepo.gpg'])
            do(['rm', '-f', self.path + '/etc/apt/trusted.gpg.d/elbe-cdtargetrepo.gpg'])

    def cdrom_mount(self):
        if self.xml.has('project/mirror/cdrom'):
            cdrompath = self.rfs.fname('cdrom')
            do(['mkdir', '-p', cdrompath])
            do(['mount', '-o', 'loop', self.xml.text('project/mirror/cdrom'), cdrompath])

    def convert_asc_to_gpg(self, infile_asc, outfile_gpg):
        with open(self.rfs.fname(infile_asc)) as pubkey:
            binpubkey = unarmor_openpgp_keyring(pubkey.read())
            with open(self.rfs.fname(outfile_gpg), 'wb') as outfile:
                outfile.write(binpubkey)

    def __enter__(self):
        suite = self.xml.text('project/suite')

        if os.path.exists(self.path + '/../repo/pool'):
            do(['mv', self.path + '/../repo', self.path])
            do(f'echo "deb copy:///repo {suite} main" > '
               f'{self.path}/etc/apt/sources.list.d/local.list')
            do(f'echo "deb-src copy:///repo {suite} main" >> '
               f'{self.path}/etc/apt/sources.list.d/local.list')

        self.cdrom_mount()
        self.rfs.__enter__()

        if self.xml.has('project/mirror/cdrom'):
            self.convert_asc_to_gpg('/cdrom/repo.pub', '/etc/apt/trusted.gpg.d/elbe-cdrepo.gpg')
            self.convert_asc_to_gpg('/cdrom/targetrepo/repo.pub',
                                    '/etc/apt/trusted.gpg.d/elbe-cdtargetrepo.gpg')

        if os.path.exists(os.path.join(self.rfs.path, 'repo/pool')):
            self.convert_asc_to_gpg('/repo/repo.pub', '/etc/apt/trusted.gpg.d/elbe-localrepo.gpg')

        return self

    def __exit__(self, typ, value, traceback):
        self.rfs.__exit__(typ, value, traceback)
        self.cdrom_umount()
        if os.path.exists(self.path + '/repo'):
            do(['mv', self.path + '/repo', self.path + '/../'])
            do(['rm', self.path + '/etc/apt/sources.list.d/local.list'])
            do(['rm', self.path + '/etc/apt/trusted.gpg.d/elbe-localrepo.gpg'])

    def _cleanup_bootstrap(self):
        # debootstrap helpfully copies configuration into the new tree
        # elbe is managing these files already
        for f in {'/etc/resolv.conf', '/etc/hostname'}:
            self.rfs.remove(f)

    def import_debootstrap_key(self, key):
        if key:
            k = strip_leading_whitespace_from_lines(key)
            return self.add_key(unarmor_openpgp_keyring(k), 'elbe-xml-primary-key.gpg')

    def _strapcmd(self, arch, suite, cross):
        primary_mirror = self.xml.get_primary_mirror(
            self.rfs.fname('/cdrom/targetrepo'), hostsysroot=self.hostsysroot)

        keyring = False
        strapcmd = ['debootstrap']

        # Should we use a special bootstrap variant?
        if self.xml.has('target/debootstrap/variant'):
            strapcmd.extend(['--variant', self.xml.text('target/debootstrap/variant')])

        # Should we include additional packages into bootstrap?
        if self.xml.has('target/debootstrap/include'):
            strapcmd.extend(['--include', self.xml.text('target/debootstrap/include')])

        # Should we exclude some packages from bootstrap?
        if self.xml.has('target/debootstrap/exclude'):
            strapcmd.extend(['--exclude', self.xml.text('target/debootstrap/exclude')])

        if cross:
            strapcmd.append('--foreign')

        if self.xml.has('project/noauth'):
            strapcmd.append('--no-check-gpg')
        elif self.xml.has('project/mirror/cdrom'):
            strapcmd.extend(['--keyring', self.rfs.fname('/elbe.keyring')])
            keyring = True
        else:
            primary_key = self.xml.get_primary_key(self.rfs.fname('/cdrom/targetrepo'),
                                                   hostsysroot=self.hostsysroot)
            debootstrap_key_path = self.import_debootstrap_key(primary_key)
            if debootstrap_key_path:
                strapcmd.extend(['--keyring', debootstrap_key_path])
                keyring = True

        strapcmd.extend(['--arch', arch, suite, self.rfs.path, primary_mirror])

        return strapcmd, keyring

    def debootstrap(self, arch='default'):

        cleanup = False
        suite = self.xml.prj.text('suite')

        if self.xml.prj.has('mirror/primary_proxy'):
            os.environ['no_proxy'] = '10.0.2.2,localhost,127.0.0.1'
            proxy = self.xml.prj.text('mirror/primary_proxy')
            proxy = proxy.strip().replace('LOCALMACHINE', '10.0.2.2')
            os.environ['http_proxy'] = proxy
            os.environ['https_proxy'] = proxy
        else:
            os.environ['no_proxy'] = ''
            os.environ['http_proxy'] = ''
            os.environ['https_proxy'] = ''

        os.environ['LANG'] = 'C'
        os.environ['LANGUAGE'] = 'C'
        os.environ['LC_ALL'] = 'C'
        os.environ['DEBIAN_FRONTEND'] = 'noninteractive'
        os.environ['DEBONF_NONINTERACTIVE_SEEN'] = 'true'

        logging.info('Debootstrap log')

        if arch == 'default':
            arch = self.xml.text('project/buildimage/arch', key='arch')

        host_arch = dpkg_architecture()
        cross = self.xml.is_cross(host_arch)

        try:
            self.cdrom_mount()
            cmd, keyring = self._strapcmd(arch, suite, cross)
            if keyring and self.xml.has('project/mirror/cdrom'):
                self.convert_asc_to_gpg('/cdrom/targetrepo/repo.pub', '/elbe.keyring')
            do(cmd)

            if cross:
                ui = '/usr/share/elbe/qemu-elbe/' + self.xml.defs['userinterpr']

                if not os.path.exists(ui):
                    ui = '/usr/bin/' + self.xml.defs['userinterpr']

                do(['cp', ui, self.rfs.fname('usr/bin')])

                if self.xml.has('project/noauth'):
                    chroot(self.rfs.path,
                           ['/debootstrap/debootstrap', '--no-check-gpg', '--second-stage'])
                else:
                    chroot(self.rfs.path,
                           ['/debootstrap/debootstrap', '--second-stage'])

            self._cleanup_bootstrap()

            if cross:
                chroot(self.rfs.path, ['dpkg', '--configure', '-a'])

        except subprocess.CalledProcessError as e:
            cleanup = True
            raise DebootstrapException() from e
        finally:
            self.cdrom_umount()
            if cleanup:
                self.rfs.rmtree('/')

    def add_key(self, key, keyname):
        """
        Adds the binary OpenPGP keyring 'key' as a trusted apt keyring
        with file name 'keyname'.
        """
        self.rfs.mkdir_p('/etc/apt/trusted.gpg.d')
        keyfile = self.rfs.fname(f'/etc/apt/trusted.gpg.d/{keyname}')
        with open(keyfile, 'wb') as outfile:
            outfile.write(key)

        return keyfile

    def import_keys(self):
        if self.xml.has('project/mirror/url-list'):
            # Should we use self.xml.prj.has("noauth")???
            #
            # If so, this is related to issue #220 -
            # https://github.com/Linutronix/elbe/issues/220
            #
            # I could make a none global 'noauth' flag for mirrors
            for i, url in enumerate(self.xml.node('project/mirror/url-list')):
                if url.has('raw-key'):
                    key = strip_leading_whitespace_from_lines(url.text('raw-key'))
                    self.add_key(unarmor_openpgp_keyring(key), f'elbe-xml-raw-key{i}.gpg')

    def initialize_dirs(self, build_sources=False):
        mirror = self.xml.create_apt_sources_list(build_sources=build_sources,
                                                  hostsysroot=self.hostsysroot)

        if self.rfs.lexists('etc/apt/sources.list'):
            self.rfs.remove('etc/apt/sources.list')

        self.rfs.write_file('etc/apt/sources.list', 0o644, mirror)

        self.rfs.mkdir_p('var/cache/elbe')

        preseed = get_preseed(self.xml)
        preseed_txt = preseed_to_text(preseed)
        self.rfs.write_file('var/cache/elbe/preseed.txt', 0o644, preseed_txt)
        with self.rfs:
            chroot(self.rfs.path, ['debconf-set-selections', '/var/cache/elbe/preseed.txt'])

    def seed_etc(self):
        passwd = self.xml.text('target/passwd_hashed')
        chroot(self.rfs.path, ['chpasswd', '--encrypted'], input=b'root:' + passwd.encode('ascii'))

        hostname = self.xml.text('target/hostname')
        fqdn = hostname
        if self.xml.has('target/domain'):
            fqdn = (f"{hostname}.{self.xml.text('target/domain')}")

        self.rfs.append_file('/etc/hosts',
                             '\n127.0.0.1 localhost'
                             f'\n127.0.1.1 {fqdn} {hostname} elbe-daemon\n')

        self.rfs.write_file('/etc/hostname', 0o644, hostname)
        self.rfs.write_file('/etc/mailname', 0o644, fqdn)

        if self.xml.has('target/console'):
            serial_con, serial_baud = self.xml.text(
                'target/console').split(',')
            if serial_baud:
                if self.rfs.exists('/etc/inittab'):
                    self.rfs.append_file(
                        '/etc/inittab',
                        f'T0:23:respawn:/sbin/getty -L {serial_con} {serial_baud} vt100\n')

                if self.rfs.exists('/lib/systemd/system/serial-getty@.service'):
                    self.rfs.symlink(
                        '/lib/systemd/system/serial-getty@.service',
                        f'/etc/systemd/system/getty.target.wants/serial-getty@{serial_con}.service',
                        allow_exists=True,
                    )

            else:
                logging.error('parsing console tag failed, needs to be of '
                              "'/dev/ttyS0,115200' format.")
