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
build into an initvm. It is meant to be used inside a container (or any
other environment) that already provides the isolation an initvm would
otherwise provide, and is therefore the VM-free alternative to
*elbe initvm submit*.

If no ELBE build daemon is reachable on *--host*/*--port* yet, *elbe
build* automatically starts one locally, detached in the background, so
that it keeps running and can serve subsequent *elbe build* invocations.

Since it is meant for container builds where there is no initvm,
packages needed only for the initvm are always excluded from the
generated CDROMs.

OPTIONS
=======

--host <hostname>
   ip or hostname of the elbe-deamon (defaults to localhost, which is
   the default, where an initvm would be listening).

--port <N>
   Port of the soap interface on the elbe-daemon.

--soaptimeout <N>
   Timeout in seconds for the soap connection. (Defaults to *90*, or the
   *ELBE_SOAPTIMEOUT_SECS* environment variable.)

--retries <N>
   How many times to retry the connection to the server before giving
   up. (Default is 10 times, yielding 10 seconds.)

--no-local-daemon
   Don't automatically start a local *elbe daemon* if *--host*/*--port*
   is not reachable yet; fail instead.

--skip-download
   After the build has finished, the generated files are downloaded
   from the daemon to the host. This step is skipped, when this option
   is specified.

--output <dir>
   Directory name where the generated and downloaded files should be
   saved. The default is to generate a directory with a timestamp in
   the current working directory.

--skip-build-bin
   Skip building binary repository CDROM, for exact reproduction.

--skip-build-sources
   Skip building source CDROM.

--keep-files
   Don’t delete elbe project files after a build. Use *elbe control
   list_projects* to get a list of available projects.

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
container definition in *contrib/containerfile-vmless* provides a
ready-to-use build environment for this.

-  Build the container image, installing elbe from the published elbe
   archive:

   ::

      $ cd contrib/containerfile-vmless
      $ make build

-  Alternatively, build the container image with ELBE packages
   built from the current checkout, instead of the published ones:

   ::

      $ cd contrib/containerfile-vmless
      $ make build-local

-  Run the build in a container, with the current directory
   mounted as */build*. Since no elbe daemon is reachable yet, *elbe
   build* starts one automatically inside the container. The container
   is removed again once the build finishes:

   ::

      $ podman run --rm --device /dev/fuse --cap-add CAP_SYS_ADMIN \
            -v $(pwd):/build:Z \
            elbe-buildenv-image \
            elbe build --skip-build-bin --skip-build-sources \
                  /build/tests/base-extended/simple-validation/image-base-trixie.xml \
                  --output /build/out

SEE ALSO
========

``elbe-initvm(1)``, ``elbe-daemon(1)``, ``elbe-control(1)``,
``elbe-preprocess(1)``

ELBE
====

Part of the ``elbe(1)`` suite
