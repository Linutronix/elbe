======================
ELBE technical Details
======================

This article describes the qemu features ELBE is using.

One essential point to understand is that qemu combines two
fundamentally different functionalities, which can also be used
independently and that ELBE uses both of them separately:

-  Virtualization (running a machine-in-a-machine)
-  Emulation (running foreign machine-code)

Both are traditionally used in combination (to run, for example, a full
ARM-based Android mobile device on an x86-based development machine).
ELBE, however, uses both functionalities separately, each one without
the other:

At the outside, ‘elbe initvm’ runs a full virtual machine with the host
system’s architecture, using the kvm technology. On a typical x86-based
host, this VM still runs x86 code at full efficiency, but does so in a
fully encapsulated environment, running its own kernel with virtualized
devices in it own root-file resides in a single file (buildenv.img) on
the hosts file system. This virtual machine must be booted before it can
be used and communication happens through its virtual console or through
virtual network connections.

At the inside, ‘elbe chroot’ runs a CPU emulation environment without
machine virtualization. This command actually does two separate things
at once:

-  chroot - i.e. divert all child processes to view a certain directory
   as their root. Within this directory, there is a full set of
   subdirectories (/etc, /usr, /var, …) and the child processes cannot
   see or access anything outside this directory.

-  qemu-user-binfmt - i.e. register qemu in such a way that binaries of
   the target architecture (e.g. ARM) are transparently called via qemu
   (this fairly complex technique is documented e.g. on
   https://wiki.debian.org/QemuUserEmulation)

The effect is that inside this ‘elbe chroot’ environment target .deb
packages can be deployed and target binaries executed. However, there is
not kernel running in the target architecture and the devices are still
those provided by the encapsulating initvm virtual machine.

While at the ‘elbe initvm’ boundary, the outside can only see a single
‘qemu’ process and a single ‘buildenv.img’ file, the ‘elbe chroot’
boundary is much more transparent, allowing the outside to observe
individual processes and files of the inner environment.
