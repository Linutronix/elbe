# ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (c) 2013-2014, 2016 Torben Hohn <torben.hohn@linutronix.de>
# Copyright (c) 2014, 2017-2018 Manuel Traut <manut@linutronix.de>
# Copyright (c) 2014 Sebastian Andrzej Siewior <bigeasy@linutronix.de>
# Copyright (c) 2016 Anna-Maria Gleixner <anna-maria@linutronix.de>
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import print_function

import random
import sys

from elbepack.kvm import find_kvm_exe

armel_defaults = {
    "arch": "armel",
    "interpreter": "qemu-system-arm",
    "interpreterversion": "0.0.0",
    "userinterpr": "qemu-arm-static",
    "console": "ttyAMA0,115200n1",
    "machine": "versatilepb",
    "nicmodel": "smc91c111",
    "triplet": "arm-linux-gnueabi",
    "sdkarch": "arm-linux-gnueabi",
}

armel_linaro48_defaults = {
    "arch": "armel",
    "interpreter": "qemu-system-arm",
    "interpreterversion": "0.0.0",
    "userinterpr": "qemu-arm-static",
    "console": "ttyAMA0,115200n1",
    "machine": "versatilepb",
    "nicmodel": "smc91c111",
    "triplet": "arm-linux-gnueabi",
    "sdkarch": "arm-linux-gnueabi",
    "toolchaintype": "linaro_armel",
    "toolchainver": "4.8.3",
}

armel_virtio_defaults = {
    "arch": "armel",
    "interpreter": "qemu-system-arm-virtio",
    "interpreterversion": "0.0.0",
    "userinterpr": "qemu-arm-static",
    "console": "ttyAMA0,115200n1",
    "machine": "versatilepb",
    "nicmodel": "smc91c111",
    "triplet": "arm-linux-gnueabi",
    "sdkarch": "arm-linux-gnueabi",
}

armhf_defaults = {
    "arch": "armhf",
    "interpreter": "qemu-system-arm",
    "interpreterversion": "0.0.0",
    "userinterpr": "qemu-arm-static",
    "console": "ttyAMA0,115200n1",
    "machine": "versatilepb -cpu cortex-a9",
    "nicmodel": "smc91c111",
    "triplet": "arm-linux-gnueabihf",
    "sdkarch": "arm-linux-gnueabihf",
}

armhf_linaro48_defaults = {
    "arch": "armhf",
    "interpreter": "qemu-system-arm",
    "interpreterversion": "0.0.0",
    "userinterpr": "qemu-arm-static",
    "console": "ttyAMA0,115200n1",
    "machine": "versatilepb -cpu cortex-a9",
    "nicmodel": "smc91c111",
    "triplet": "arm-linux-gnueabihf",
    "toolchaintype": "linaro",
    "toolchainver": "4.8.3",
}

armhf_virtio_defaults = {
    "arch": "armhf",
    "interpreter": "qemu-system-arm-virtio",
    "interpreterversion": "0.0.0",
    "userinterpr": "qemu-arm-static",
    "console": "ttyAMA0,115200n1",
    "machine": "versatilepb -cpu cortex-a9",
    "nicmodel": "virtio",
    "triplet": "arm-linux-gnueabihf",
    "sdkarch": "arm-linux-gnueabihf",
}

aarch64_defaults = {
    "arch": "arm64",
    "interpreter": "qemu-system-aarch64",
    "interpreterversion": "0.0.0",
    "userinterpr": "qemu-aarch64-static",
    "console": "ttyAMA0,115200n1",
    "machine": "virt -cpu cortex-a57",
    "nicmodel": "virtio",
    "triplet": "aarch64-linux-gnu",
    "sdkarch": "aarch64-linux-gnu",
}

ppc_defaults = {
    "arch": "powerpc",
    "interpreter": "qemu-system-ppc",
    "interpreterversion": "0.0.0",
    "userinterpr": "qemu-ppc-static",
    "console": "ttyPZ0,115200n1",
    "machine": "mac99",
    "nicmodel": "rtl8139",
    "triplet": "powerpc-linux-gnu",
    "sdkarch": "powerpc-linux-gnu",
}

ppcspe_defaults = {
    "arch": "powerpcspe",
    "interpreter": "qemu-system-ppc",
    "interpreterversion": "0.0.0",
    "userinterpr": "qemu-ppc-static",
    "console": "ttyS0,115200n1",
    "machine": "mpc8544ds",
    "nicmodel": "rtl8139",
    "triplet": "powerpc-linux-gnuspe",
}

ppc64el_defaults = {
    "arch": "ppc64el",
    "interpreter": "qemu-system-ppc64",
    "interpreterversion": "0.0.0",
    "userinterpr": "qemu-ppc64le-static",
    "console": "ttyS0,115200n1",
    "machine": "none",
    "nicmodel": "virtio",
    "triplet": "ppc64le-linux-gnu",
    "sdkarch": "powerpc64le-linux-gnu",
}

amd64_defaults = {
    "arch": "amd64",
    "interpreter": find_kvm_exe()[0],
    "interpreterversion": find_kvm_exe()[1],
    "console": "ttyS0,115200n1",
    "machine": "pc",
    "nicmodel": "virtio",
    "triplet": "x86_64-linux-gnu",
}

i386_defaults = {
    "arch": "i386",
    "interpreter": "kvm",
    "interpreterversion": "0.0.0",
    "console": "ttyS0,115200n1",
    "machine": "pc",
    "nicmodel": "virtio",
    "triplet": "i386-linux-gnu",
}

archindep_defaults = {
    "name": "elbe-buildenv",
    "size": "20G",
    "img": "qcow2",
    "mem": "1GiB",
    "swap-size": "0",
    "max-cpus": "8"
}

defaults = {"armel": armel_defaults,
            "armel-linaro48": armel_linaro48_defaults,
            "armel-virtio": armel_virtio_defaults,
            "armhf": armhf_defaults,
            "armhf-linaro48": armhf_linaro48_defaults,
            "armhf-virtio": armhf_virtio_defaults,
            "aarch64": aarch64_defaults,
            "ppc": ppc_defaults,
            "ppcspe": ppcspe_defaults,
            "ppc64el": ppc64el_defaults,
            "amd64": amd64_defaults,
            "i386": i386_defaults,
            "nodefaults": {}}

def get_random_mac():
    binaddr = [random.randint(0, 255) for _ in range(6)]
    binaddr[0] &= 0xfe
    binaddr[0] |= 0x02
    s = ["%02x" % x for x in binaddr]

    return ':'.join(s)


class ElbeDefaults(object):

    def __init__(self, build_type):

        if build_type not in defaults:
            print("Please specify a valid buildtype.")
            print("Valid buildtypes:")
            print(defaults.keys())
            print("Please specify a valid buildtype.")
            print("Valid buildtypes:")
            print(list(defaults.keys()))
            sys.exit(20)

        self.defaults = defaults[build_type]
        self.defaults["nicmac"] = get_random_mac()

        self.generic_defaults = archindep_defaults

    def __getitem__(self, key):
        if key in self.defaults:
            return self.defaults[key]
        if key in self.generic_defaults:
            return self.generic_defaults[key]

        return None
