************************
elbe-buildsysroot
************************

NAME
====

elbe-buildsysroot - Build a sysroot archive.

SYNOPSIS
========

   ::

      elbe buildsysroot \
              [ --buildtype <type> ] \
              [ --skip-validation ] \
              <builddir>

DESCRIPTION
===========

*elbe buildsysroot* builds a sysroot tar archive from the given build
directory (built with ``elbe-buildchroot(1)`` before), containing the
libraries and header files of the root filesystem. This can be used for
cross-compiling. For example, if a Linaro 2014.02 toolchain is used, the
archive can be unpacked into
*gcc-linaro-arm-linux-gnueabihf-\*/arm-linux-gnueabihf/libc* to set up a
cross-toolchain for the given root filesystem.

The archive will be created as *sysroot.tar.xz* in the build directory.

This command has to be run as root **inside the Elbe build VM**.

Please note that the package *symlinks* has to be included in the
package list of the project for this to work, as well as the relevant
development packages. The XML file of the project also needs a *triplet*
definition.

OPTIONS
=======

--buildtype <buildtype>
   Override the build type specified in the XML file.

--skip-validation
   Skip the validation of the XML file. (Not recommended)

<builddir>
   The build directory to generate the sysroot archive from.

EXAMPLES
========

-  Build a sysroot archive from the project located at */root/myarm*

   ::

      # elbe buildsysroot /root/myarm

ELBE
====

Part of the ``elbe(1)`` suite
