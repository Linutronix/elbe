************************
elbe-debianize
************************

NAME
====

elbe-debianize - How to debianize software

DESCRIPTION
===========

*elbe debianize* used to be a command that generated a *debian*
directory inside a source tree of the Linux kernel, U-Boot, or Barebox.
The templates that the command used for that directory do not follow
Debian’s best practices and broke for Linux >= 5.16. Therefore, *elbe
debianize* was removed and is no longer supported.

In order to package U-Boot, please use the u-boot source package from
the Debian archive. Modifying it for your target architecture or a
vendor source tree should be straight-forward.

For Barebox, there is no alternative currently. However, Debian bug
#900958 asks for a barebox package. When that is resolved, please refer
to that package.

Linux >= 6.4 provides a built-in make target 'srcdeb-pkg' to debianize the
kernel. Just be sure to configure the kernel so that a .config file is
available, and to set the variables that are evaluated by the script. See this
man page’s EXAMPLES section. After the source package is built, there is one
generated file that does not belong to an unbuilt debian directory:
debian/files. For older Linux versions without 'srcdeb-pkg' one can instead use
the long existing 'deb-pkg' target, but must set the make variable
DPKG_FLAGS=-S to skip the binary package build.

Instead of specifying a specific defconfig the .config will end up being
used. There is no compiler prefix embedded in debian/rules for cross
compilation, so you need to specify it while building the package.

This will only generate the source package format that is specified in
the Linux tree, which is 1.0 for versions < 6.3. The resulting kernel
image format will be the default for the build architecture and the
uImage load address is not included in the debian directory but it
should be derived from some defconfig value if needed.

Several Linux versions will not generate all the Build-Depends that are
needed to build in a clean environment and you will probably need to fix
them manually.

EXAMPLES
========

In order to debianize and build a stable kernel for an arm64 system use
the following commands. Most of the environment and make variables are
optional but demonstrate the replacements for the *elbe debianize*
fields.

+

::

   $ git clone git://git.kernel.org/pub/scm/linux/kernel/git/stable/linux-stable.git
   $ cd linux-stable
   $ export CROSS_COMPILE=aarch64-linux-gnu-
   $ export DEBEMAIL="`git config user.name` <`git config user.email`>"
   $ export KDEB_CHANGELOG_DIST=unstable
   $ make ARCH=arm64 defconfig
   $ make ARCH=arm64 KERNELRELEASE=6.12-elbe srcdeb-pkg
   $ rm debian/files
   $ git add -f debian
   $ git commit -sm 'add the srcdeb-pkg generated debianization'
   $ CC=aarch64-linux-gnu-gcc dpkg-buildpackage -b -aarm64
