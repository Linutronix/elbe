************************
elbe-build
************************

NAME
====

elbe-build - Build a root filesystem from an ELBE XML file, without
requiring an initvm.

SYNOPSIS
========

   ::

      elbe build [options] <xmlfile> | <isoimage>

DESCRIPTION
===========

This command builds an ELBE project directly, without encapsulating the
build into an initvm and without any daemon or SOAP communication. It
runs the whole build in-process, and is meant to be used in an
environment that already provides the isolation an initvm would
otherwise provide. It is therefore the VM-free alternative to
*elbe initvm submit*.

Since it is meant for builds where there is no initvm, packages
needed only for the initvm are always excluded from the generated CDROMs.

OPTIONS
=======

--skip-download
   After the build has finished, the generated files are normally
   copied out of the project directory to *--build-dir*. This step is
   skipped, when this option is specified.

--build-dir <dir>
   Directory name where the generated and downloaded files should be
   saved and where the internal build cache is kept. The default is to
   generate a directory with a timestamp in the current working directory.

--skip-build-bin
   Skip building binary repository CDROM, for exact reproduction.

--skip-build-sources
   Skip building source CDROM.

--keep-files
   Don’t delete elbe project files after a build. The project directory
   is printed during the build.

--writeproject <file>
   Write project name to <file>.

--build-sdk
   Also build an SDK.

--base-image <base-image-file>
   Use a base image instead of debootstrap as the starting point for a rootfilesystem (experimental).

XML OPTIONS
===========

These options are passed through to an implicit invocation of
*elbe preprocess*, which is run on the given xmlfile before the build.

-v <variants>, --variants <variants>
   comma separated list of variants; enable only tags with empty or
   given variant.

-p <proxy>, --proxy <proxy>
   add proxy to mirrors


Prepare Container
=================

Since, in contrast to the initvm command, the build command does not provide
any isolation of the build environment itself, it is useful to encapsulate
the build into a container. 

The container definition in *contrib/containerfile* provides a
ready-to-use build environment for this.

-  Build the container image, installing elbe from the published elbe
   archive:

   ::

      $ cd contrib/containerfile
      $ make build

-  Alternatively, build the container image with ELBE packages
   built from the current checkout, instead of the published ones:

   ::

      $ cd contrib/containerfile
      $ make build-local


Run Build in Rootless Container
===============================

For highest security and convenience, running build in a rootless Podman
container is preferred. This, however, only enables a reduced feature set
of ELBE as discussed in more detail in the next section.

For scenarios where the reduced feature set is sufficient, a build command
can be simply executed as a normal user with

   ::

      podman run --rm \
            -v $(pwd):/work:Z \
            elbe-buildenv-image \
            elbe build /work/myimage.xml --build-dir /work/build


Run Build in Rootful Container
==============================

In order to use the full feature set of ELBE, elevated privileges are required.
In particular, these elevanted privileges are needed for the the following features:

-  ``<grub-install>``
-  ``<device-command>`` or ``<path-command>`` inside ``<fstab>``
   (including the related ``<tune2fs>``)
- ``<mknod>`` inside ``<finetuning>``
-  a ``<losetup>`` project-finetuning action containing
   ``copy_from_partition``, ``copy_to_partition``, or ``command``

To enable them, a full build command could look like this:

   ::

      pkexec podman run --rm \
            -v $(pwd):/work:Z \
            --cap-add SYS_ADMIN \
            --cap-add MKNOD \
            --device-cgroup-rule', 'b *:* rmw \
            --device', '/dev/loop-control \
            -v /dev:/dev \
            -v /run/udev:/run/udev:ro \
            --network host \
            --security-opt apparmor=unconfined \
            elbe-buildenv-image \
            elbe build /work/myimage.xml --build-dir /work/build


These elevated privileges expose several potential attack vectors, and
containerization does not mitigate these risks compared to performing
the build directly on the host. Therefore, in this scenario,
containerization should not be considered a security feature, but solely
as a means of simplifying the environment setup.


SEE ALSO
========

``elbe-initvm(1)``, ``elbe-preprocess(1)``

ELBE
====

Part of the ``elbe(1)`` suite
