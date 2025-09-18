# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2013-2018 Linutronix GmbH

import random

armel_defaults = {
    'arch': 'armel',
    'interpreter': 'qemu-system-arm',
    'userinterpr': 'qemu-arm-static',
    'console': 'ttyAMA0,115200n1',
    'machine': 'versatilepb',
    'nicmodel': 'smc91c111',
    'triplet': 'arm-linux-gnueabi',
    'sdkgccpkg': 'g++-arm-linux-gnueabi',
    'elfcode': 'ARM',
}

armel_linaro48_defaults = {
    'arch': 'armel',
    'interpreter': 'qemu-system-arm',
    'userinterpr': 'qemu-arm-static',
    'console': 'ttyAMA0,115200n1',
    'machine': 'versatilepb',
    'nicmodel': 'smc91c111',
    'triplet': 'arm-linux-gnueabi',
    'sdkgccpkg': 'g++-arm-linux-gnueabi',
    'toolchaintype': 'linaro_armel',
    'toolchainver': '4.8.3',
    'elfcode': 'ARM',
}

armhf_defaults = {
    'arch': 'armhf',
    'interpreter': 'qemu-system-arm',
    'userinterpr': 'qemu-arm-static',
    'console': 'ttyAMA0,115200n1',
    'machine': 'versatilepb -cpu cortex-a9',
    'nicmodel': 'smc91c111',
    'triplet': 'arm-linux-gnueabihf',
    'sdkgccpkg': 'g++-arm-linux-gnueabihf',
    'elfcode': 'ARM',
}

armhf_linaro48_defaults = {
    'arch': 'armhf',
    'interpreter': 'qemu-system-arm',
    'userinterpr': 'qemu-arm-static',
    'console': 'ttyAMA0,115200n1',
    'machine': 'versatilepb -cpu cortex-a9',
    'nicmodel': 'smc91c111',
    'triplet': 'arm-linux-gnueabihf',
    'toolchaintype': 'linaro',
    'toolchainver': '4.8.3',
    'elfcode': 'ARM',
}

aarch64_defaults = {
    'arch': 'arm64',
    'interpreter': 'qemu-system-aarch64',
    'userinterpr': 'qemu-aarch64-static',
    'console': 'ttyAMA0,115200n1',
    'machine': 'virt -cpu cortex-a57',
    'nicmodel': 'virtio',
    'triplet': 'aarch64-linux-gnu',
    'sdkgccpkg': 'g++-aarch64-linux-gnu',
    'elfcode': 'ARM aarch64',
}

ppc_defaults = {
    'arch': 'powerpc',
    'interpreter': 'qemu-system-ppc',
    'userinterpr': 'qemu-ppc-static',
    'console': 'ttyPZ0,115200n1',
    'machine': 'mac99',
    'nicmodel': 'rtl8139',
    'triplet': 'powerpc-linux-gnu',
    'sdkgccpkg': 'g++-powerpc-linux-gnu',
    'elfcode': 'PowerPC or cisco 4500',
}

ppcspe_defaults = {
    'arch': 'powerpcspe',
    'interpreter': 'qemu-system-ppc',
    'userinterpr': 'qemu-ppc-static',
    'console': 'ttyS0,115200n1',
    'machine': 'mpc8544ds',
    'nicmodel': 'rtl8139',
    'triplet': 'powerpc-linux-gnuspe',
}

ppc64el_defaults = {
    'arch': 'ppc64el',
    'interpreter': 'qemu-system-ppc64',
    'userinterpr': 'qemu-ppc64le-static',
    'console': 'ttyS0,115200n1',
    'machine': 'none',
    'nicmodel': 'virtio',
    'triplet': 'powerpc64le-linux-gnu',
    'sdkgccpkg': 'g++-powerpc64le-linux-gnu',
    'elfcode': '64-bit PowerPC or cisco 7500',
}

amd64_defaults = {
    'arch': 'amd64',
    'interpreter': 'qemu-system-x86_64',
    'console': 'ttyS0,115200n1',
    'machine': 'pc',
    'nicmodel': 'virtio',
    'triplet': 'x86_64-linux-gnu',
    'sdkgccpkg': 'g++',
    'elfcode': 'x86-64',
}

i386_defaults = {
    'arch': 'i386',
    'interpreter': 'kvm',
    'console': 'ttyS0,115200n1',
    'machine': 'pc',
    'nicmodel': 'virtio',
    'triplet': 'i686-linux-gnu',
    'sdkgccpkg': 'g++-i686-linux-gnu',
    'elfcode': 'Intel 80386',
}

riscv64_defaults = {
    'arch': 'riscv64',
    'interpreter': 'qemu-system-riscv64',
    'userinterpr': 'qemu-riscv64-static',
    'console': 'ttyS0,115200n1',
    'machine': 'sifive_u',
    'nicmodel': 'virtio',
    'triplet': 'riscv64-linux-gnu',
    'sdkgccpkg': 'g++-riscv64-linux-gnu',
    'elfcode': 'RISC-V 64 bit',
}

archindep_defaults = {
    'name': 'elbe-buildenv',
    'size': '20G',
    'img': 'qcow2',
    'mem': '1GiB',
    'swap-size': '0',
    'max-cpus': '8',
    'sdkarch': 'amd64',
}

defaults = {'armel': armel_defaults,
            'armel-linaro48': armel_linaro48_defaults,
            'armhf': armhf_defaults,
            'armhf-linaro48': armhf_linaro48_defaults,
            'aarch64': aarch64_defaults,
            'ppc': ppc_defaults,
            'ppcspe': ppcspe_defaults,
            'ppc64el': ppc64el_defaults,
            'amd64': amd64_defaults,
            'i386': i386_defaults,
            'riscv64': riscv64_defaults,
            'nodefaults': {}}


def get_random_mac():
    binaddr = [random.randint(0, 255) for _ in range(6)]
    binaddr[0] &= 0xfe
    binaddr[0] |= 0x02
    s = [f'{x:02x}' for x in binaddr]

    return ':'.join(s)


class ElbeDefaults:

    def __init__(self, build_type):

        assert build_type in defaults, ('Invalid buildtype %s\n'
                                        'Valid buildtypes are:\n  - %s' %
                                        (build_type, '\n  - '.join(defaults.keys())))

        self.defaults = defaults[build_type]
        self.defaults['nicmac'] = get_random_mac()

        self.generic_defaults = archindep_defaults

    def __getitem__(self, key):
        if key in self.defaults:
            return self.defaults[key]
        if key in self.generic_defaults:
            return self.generic_defaults[key]

        return None
