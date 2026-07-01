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

SEE ALSO
========

``elbe-initvm(1)``, ``elbe-preprocess(1)``

ELBE
====

Part of the ``elbe(1)`` suite
