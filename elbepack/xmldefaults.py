
import random
import string
import sys

armel_defaults = {
        "arch":         "armel",
        "size":         "20G",
        "mem":          "256",
        "interpreter":  "qemu-system-arm",
        "userinterpr":  "qemu-arm-static",
        "console":      "ttyAMA0,115200n1",
        "machine":      "versatilepb",
        "nicmodel":     "smc91c111",
        "triplet":      "arm-linux-gnueabi"
}

armel_linaro48_defaults = {
        "arch":         "armel",
        "size":         "20G",
        "mem":          "256",
        "interpreter":  "qemu-system-arm",
        "userinterpr":  "qemu-arm-static",
        "console":      "ttyAMA0,115200n1",
        "machine":      "versatilepb",
        "nicmodel":     "smc91c111",
        "triplet":      "arm-linux-gnueabi",
        "toolchaintype":"linaro_armel",
        "toolchainver": "4.8.3",
}

armel_virtio_defaults = {
        "arch":         "armel",
        "size":         "20G",
        "mem":          "256",
        "interpreter":  "qemu-system-arm-virtio",
        "userinterpr":  "qemu-arm-static",
        "console":      "ttyAMA0,115200n1",
        "machine":      "versatilepb",
        "nicmodel":     "smc91c111",
        "triplet":      "arm-linux-gnueabi"
}

armhf_defaults = {
        "arch":         "armhf",
        "size":         "20G",
        "mem":          "256",
        "interpreter":  "qemu-system-arm",
        "userinterpr":  "qemu-arm-static",
        "console":      "ttyAMA0,115200n1",
        "machine":      "versatilepb -cpu cortex-a9",
        "nicmodel":     "smc91c111",
        "triplet":      "arm-linux-gnueabihf"
}

armhf_linaro48_defaults = {
        "arch":         "armhf",
        "size":         "20G",
        "mem":          "256",
        "interpreter":  "qemu-system-arm",
        "userinterpr":  "qemu-arm-static",
        "console":      "ttyAMA0,115200n1",
        "machine":      "versatilepb -cpu cortex-a9",
        "nicmodel":     "smc91c111",
        "triplet":      "arm-linux-gnueabihf",
        "toolchaintype":"linaro",
        "toolchainver": "4.8.3",
}

armhf_virtio_defaults = {
        "arch":         "armhf",
        "size":         "20G",
        "mem":          "256",
        "interpreter":  "qemu-system-arm-virtio",
        "userinterpr":  "qemu-arm-static",
        "console":      "ttyAMA0,115200n1",
        "machine":      "versatilepb -cpu cortex-a9",
        "nicmodel":     "virtio",
        "triplet":      "arm-linux-gnueabihf"
}

ppc_defaults = {
        "arch":         "powerpc",
        "size":         "20G",
        "mem":          "256",
        "interpreter":  "qemu-system-ppc",
        "userinterpr":  "qemu-ppc-static",
        "console":      "ttyPZ0,115200n1",
        "machine":      "mac99",
        "nicmodel":     "rtl8139",
        "triplet":      "powerpc-linux-gnu"
}

ppcspe_defaults = {
        "arch":         "powerpcspe",
        "size":         "20G",
        "mem":          "512",
        "interpreter":  "qemu-system-ppc",
        "userinterpr":  "qemu-ppc-static",
        "console":      "ttyS0,115200n1",
        "machine":      "mpc8544ds",
        "nicmodel":     "rtl8139",
        "triplet":      "powerpc-linux-gnuspe"
}

amd64_defaults = {
        "arch":         "amd64",
        "size":         "20G",
        "mem":          "1024",
        "interpreter":  "kvm",
        "console":      "ttyS0,115200n1",
        "machine":      "pc",
        "nicmodel":     "virtio",
        "triplet":      "x86_64-linux-gnu"
}

i386_defaults = {
        "arch":         "i386",
        "size":         "20G",
        "mem":          "1024",
        "interpreter":  "kvm",
        "console":      "ttyS0,115200n1",
        "machine":      "pc",
        "nicmodel":     "virtio",
        "triplet":      "i386-linux-gnu"
}

archindep_defaults = {
        "kinitrd":      "elbe-bootstrap",
        "name":         "elbe-buildenv"
}

defaults = { "armel": armel_defaults,
             "armel-linaro48": armel_linaro48_defaults,
             "armel-virtio": armel_virtio_defaults,
             "armhf": armhf_defaults,
             "armhf-linaro48": armhf_linaro48_defaults,
             "armhf-virtio": armhf_virtio_defaults,
             "ppc": ppc_defaults,
             "ppcspe": ppcspe_defaults,
             "amd64": amd64_defaults,
             "i386": i386_defaults,
             "nodefaults": {}  }

xml_field_path = {
        "arch":         "project/buildimage/arch",
        "size":         "project/buildimage/size",
        "mem":          "project/buildimage/mem",
        "interpreter":  "project/buildimage/interpreter",
        "console":      "project/buildimage/console",
        "machine":      "project/buildimage/machine",
        "nicmodel":     "project/buildimage/NIC/model",
        "kinitrd":      "project/buildimage/kinitrd",
        "name":         "project/name"
}

def get_random_mac():
    binaddr = [random.randint(0,256) for i in range(6) ]
    binaddr[0] &= 0xfe
    binaddr[0] |= 0x02
    s = map( lambda x: "%02x" % x, binaddr )

    return string.join( s, ":" )


class ElbeDefaults(object):

    def __init__(self, build_type):

        if not defaults.has_key(build_type):
            print "Please specify a valid buildtype."
            print "Valid buildtypes:"
            print defaults.keys()
            sys.exit(20)

        self.defaults = defaults[build_type]
        self.defaults["nicmac"] = get_random_mac()

        self.generic_defaults = archindep_defaults

    def __getitem__( self, key ):
        if self.defaults.has_key( key ):
            return self.defaults[key]
        if self.generic_defaults.has_key( key ):
            return self.generic_defaults[key]

        return None
