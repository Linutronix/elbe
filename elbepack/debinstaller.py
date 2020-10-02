# ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (c) 2018 Torben Hohn <torben.hohn@linutronix.de>
#
# SPDX-License-Identifier: GPL-3.0-or-later

import sys
import os
import re

from shutil import copyfile
from urllib.request import urlopen

from gpg import core
from gpg.constants import PROTOCOL_OpenPGP

from elbepack.filesystem import TmpdirFilesystem
from elbepack.egpg import OverallStatus, check_signature
from elbepack.shellhelper import CommandError, system
from elbepack.hashes import HashValidator, HashValidationFailed


class InvalidSignature(Exception):
    pass


class NoKinitrdException(Exception):
    pass


class ReleaseFile(HashValidator):
    def __init__(self, base_url, fname, fname_list):

        HashValidator.__init__(self, base_url)

        header_re = re.compile(r'(\w+):(.*)')
        hash_re = re.compile(r' ([0-9a-f]+)\s+([0-9]+)\s+(\S+)')
        current_header = ''

        with open(fname, 'r') as fp:
            for l in fp.readlines():
                m = header_re.match(l)
                if m:
                    # line contains an rfc822 Header,
                    # remember it.
                    current_header = m.group(1)
                    continue

                m = hash_re.match(l)
                if m:
                    # line contains a hash entry.
                    # check filename, whether we are interested in it
                    if m.group(3) in fname_list:
                        self.insert_fname_hash(current_header,
                                               m.group(3),
                                               m.group(1))


class SHA256SUMSFile(HashValidator):
    def __init__(self, base_url, fname, fname_list):

        HashValidator.__init__(self, base_url)

        hash_re = re.compile(r'([0-9a-f]+)\s+(\S+)')

        with open(fname, 'r') as fp:
            for l in fp.readlines():
                m = hash_re.match(l)
                if m:
                    # line contains a hash entry.
                    # check filename, whether we are interested in it
                    if m.group(2) in fname_list:
                        self.insert_fname_hash("SHA256",
                                               m.group(2),
                                               m.group(1))


def setup_apt_keyring(gpg_home, keyring_fname):
    ring_path = os.path.join(gpg_home, keyring_fname)
    if not os.path.isdir("/etc/apt/trusted.gpg.d"):
        print("/etc/apt/trusted.gpg.d doesn't exist")
        print("apt-get install debian-archive-keyring may "
              "fix this problem")
        sys.exit(20)

    if os.path.exists("/etc/apt/trusted.gpg"):
        system('cp /etc/apt/trusted.gpg "%s"' % ring_path)

    gpg_options = '--keyring "%s" --no-auto-check-trustdb ' \
                  '--trust-model always --no-default-keyring ' \
                  '--batch ' \
                  '--homedir "%s"' % (ring_path, gpg_home)

    trustkeys = os.listdir("/etc/apt/trusted.gpg.d")
    for key in trustkeys:
        print("Import %s: " % key)
        try:
            system('gpg %s --import "%s"' % (
                gpg_options,
                os.path.join("/etc/apt/trusted.gpg.d", key)))
        except CommandError:
            print('adding keyring "%s" to keyring "%s" failed' % (key,
                                                                  ring_path))


def download(url, local_fname):
    try:
        system('wget -O "%s" "%s"' % (local_fname, url))
    except CommandError:
        raise NoKinitrdException('Failed to download %s' % url)


def download_release(tmp, base_url):

    # setup gpg context, for verifying
    # the Release.gpg signature.
    ctx = core.Context()
    ctx.set_engine_info(PROTOCOL_OpenPGP,
                      None,
                      tmp.fname('/'))

    # download the Relase file to a tmp file,
    # because we need it 2 times
    download(base_url + "Release", tmp.fname('Release'))

    # validate signature.
    # open downloaded plaintext file, and
    # use the urlopen object of the Release.gpg
    # directtly.
    sig = urlopen(base_url + 'Release.gpg', None, 10)
    try:
        with tmp.open("Release", "r") as signed:

            overall_status = OverallStatus()

            # verify detached signature
            det_sign = core.Data(sig.read())
            signed_data = core.Data(signed.read())
            ctx.op_verify(det_sign, signed_data, None)
            vres = ctx.op_verify_result()

            for s in vres.signatures:
                status = check_signature(ctx, s)
                overall_status.add(status)

            if overall_status.to_exitcode():
                raise InvalidSignature('Failed to verify Release file')

    finally:
        sig.close()


def download_kinitrd(tmp, suite, mirror):
    base_url = "%s/dists/%s/" % (
        mirror.replace("LOCALMACHINE", "localhost"), suite)
    installer_path = "main/installer-amd64/current/images/"

    setup_apt_keyring(tmp.fname('/'), 'pubring.gpg')

    # download release file and check
    # signature
    download_release(tmp, base_url)

    # parse Release file, and remember hashvalues
    # we are interested in
    interesting = [installer_path + 'SHA256SUMS']
    release_file = ReleaseFile(base_url, tmp.fname('Release'), interesting)

    # now download and validate SHA256SUMS
    release_file.download_and_validate_file(
            installer_path + 'SHA256SUMS',
            tmp.fname('SHA256SUMS'))

    # now we have a valid SHA256SUMS file
    # parse it
    interesting = ['./cdrom/initrd.gz',
                   './cdrom/vmlinuz',
                   './netboot/debian-installer/amd64/initrd.gz',
                   './netboot/debian-installer/amd64/linux']
    sha256_sums = SHA256SUMSFile(
            base_url + installer_path,
            tmp.fname('SHA256SUMS'),
            interesting)

    # and then download the files we actually want
    for p, ln in zip(interesting, ['initrd-cdrom.gz',
                                   'linux-cdrom',
                                   'initrd.gz',
                                   'vmlinuz']):
        sha256_sums.download_and_validate_file(
                p,
                tmp.fname(ln))


def get_primary_mirror(prj):
    if prj.has("mirror/primary_host"):
        m = prj.node("mirror")

        mirror = m.text("primary_proto") + "://"
        mirror += m.text("primary_host") + "/"
        mirror += m.text("primary_path")
    else:
        raise NoKinitrdException("Broken xml file: "
                                 "no cdrom and no primary host")

    return mirror


def copy_kinitrd(prj, target_dir):

    suite = prj.text("suite")

    try:
        tmp = TmpdirFilesystem()
        if prj.has("mirror/cdrom"):
            system('7z x -o%s "%s" initrd-cdrom.gz vmlinuz' %
                   (tmp.fname('/'), prj.text("mirror/cdrom")))

            # initrd.gz needs to be cdrom version !
            copyfile(tmp.fname("initrd-cdrom.gz"),
                     os.path.join(target_dir, "initrd.gz"))
        else:
            mirror = get_primary_mirror(prj)
            download_kinitrd(tmp, suite, mirror)

            copyfile(tmp.fname("initrd.gz"),
                     os.path.join(target_dir, "initrd.gz"))

        copyfile(tmp.fname("initrd-cdrom.gz"),
                 os.path.join(target_dir, "initrd-cdrom.gz"))

        copyfile(tmp.fname("vmlinuz"),
                 os.path.join(target_dir, "vmlinuz"))

    except IOError as e:
        raise NoKinitrdException('IoError %s' % str(e))
    except InvalidSignature as e:
        raise NoKinitrdException('InvalidSignature %s' % str(e))
    except HashValidationFailed as e:
        raise NoKinitrdException('HashValidationFailed %s' % str(e))
