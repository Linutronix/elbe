
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
        "nicmodel":     "smc91c111"
}

armel_virtio_defaults = {
        "arch":         "armel",
        "size":         "20G",
        "mem":          "256",
        "interpreter":  "qemu-system-arm-virtio",
        "userinterpr":  "qemu-arm-static",
        "console":      "ttyAMA0,115200n1",
        "machine":      "versatilepb",
        "nicmodel":     "smc91c111"
}

armhf_defaults = {
        "arch":         "armhf",
        "size":         "20G",
        "mem":          "256",
        "interpreter":  "qemu-system-arm",
        "userinterpr":  "qemu-arm-static",
        "console":      "ttyAMA0,115200n1",
        "machine":      "versatilepb -cpu cortex-a9",
        "nicmodel":     "smc91c111"
}

armhf_virtio_defaults = {
        "arch":         "armhf",
        "size":         "20G",
        "mem":          "256",
        "interpreter":  "qemu-system-arm-virtio",
        "userinterpr":  "qemu-arm-static",
        "console":      "ttyAMA0,115200n1",
        "machine":      "versatilepb -cpu cortex-a9",
        "nicmodel":     "virtio"
}

ppc_defaults = { 
        "arch":         "ppc",
        "size":         "20G", 
        "mem":          "256", 
        "interpreter":  "qemu-system-ppc",
        "userinterpr":  "qemu-ppc-static",
        "console":      "ttyPZ0,115200n1",
        "machine":      "mac99",
        "nicmodel":     "rtl8139"
}

amd64_defaults = { 
        "arch":         "amd64",
        "size":         "20G", 
        "mem":          "1024", 
        "interpreter":  "kvm",
        "console":      "ttyS0,115200n1",
        "machine":      "pc",
        "nicmodel":     "virtio"
}

i386_defaults = { 
        "arch":         "i386",
        "size":         "20G", 
        "mem":          "1024", 
        "interpreter":  "kvm",
        "console":      "ttyS0,115200n1",
        "machine":      "pc",
        "nicmodel":     "virtio"
}

defaults = { "armel": armel_defaults,
             "armel-virtio": armel_virtio_defaults,
             "armhf": armhf_defaults,
             "armhf-virtio": armhf_virtio_defaults,
             "ppc": ppc_defaults,
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
        "nicmodel":     "project/buildimage/NIC/model"
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

        def __getitem__( self, key ):
                if self.defaults.has_key( key ):
                        return self.defaults[key]

                print "No Default value has been Provided"
                print "Either use a valid buildtype, or provide the field in the xml File."
                print "The location in the xml is here:"
                print xml_field_path[key]
                sys.exit(20)








