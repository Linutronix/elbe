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
runs the whole build in-process, and is meant to be used inside a
container (or any other environment) that already provides the
isolation an initvm would otherwise provide. It is therefore the
VM-free alternative to *elbe initvm submit*.

Since it is meant for container builds where there is no initvm,
packages needed only for the initvm are always excluded from the
generated CDROMs.

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

Examples
========

*elbe build* is meant to be run inside a container. The example
container definition in *contrib/containerfile* provides a
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

-  Run the build in a container, with the current directory
   mounted as */build*. The container is removed again once the build
   finishes:

   ::

      $ podman run --rm \
            -v $(pwd):/work:Z \
            elbe-buildenv-image \
            elbe build --skip-build-bin --skip-build-sources \
                  /work/tests/base-extended/simple-validation/image-base-trixie.xml \
                  --build-dir /work/build


Rootful Containers
==================

Some project XML features make *elbe build* create a Linux loop device
to loop-mount a disk or partition image:

-  ``<grub-install>`` inside a ``<msdoshd>``/``<gpthd>`` target image
-  ``<fs-finetuning>`` (or the ``<tune2fs>``) inside a
   partition's ``<fs>``
-  a ``<losetup>`` project-finetuning action containing
   ``copy_from_partition``, ``copy_to_partition``, or ``command``

Creating a loop device requires access to */dev/loop-control*, which
is a host-kernel-wide privilege. Additionally, ``CAP_SYS_ADMIN`` must be
enabled in the **initial user namespace** (not in a namespace created
via ``unshare``), which means **rootless containers cannot create loop
devices**.

Also, some XMLs might require mknod which is also not possible
in rootless containers.

If the project XML uses one of the features above, *elbe build*
checks the requirements upfront and aborts immediately.

If your XML needs these features, either:

-  build via *elbe initvm submit* instead, which runs inside a full
   virtual machine with real root privileges, or

-  run the container with elevated privileges (i.e. no rootless container).
   Add the following to the *podman run*/*docker run* invocation and run with
   elevated privileges (e.g. via ``pkexec`` (PolicyKit)).

   ::

      --cap-add SYS_ADMIN --cap-add MKNOD --device-cgroup-rule='b *:* rmw' \
            --security-opt apparmor=unconfined

   Note that since this is now a rootful container and it there are much more
   options for security vulnerabilities to manifest. Also, the networking might
   be differently set up, so you might need to add ``--network slirp4netns``
   (or ``--network host`` if ``slirp4netns`` is not installed).

   All together, the command would look like this:

   ::

      pkexec podman run --rm \
            -v $(pwd):/work:Z \
            --cap-add SYS_ADMIN --cap-add MKNOD --device-cgroup-rule='b *:* rmw' \
            --security-opt apparmor=unconfined \
            --network slirp4netns \
            elbe-buildenv-image \
            elbe build /work/myimage.xml --build-dir /work/build

SEE ALSO
========

``elbe-initvm(1)``, ``elbe-preprocess(1)``

ELBE
====

Part of the ``elbe(1)`` suite
