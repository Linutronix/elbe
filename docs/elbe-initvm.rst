************************
elbe-initvm
************************

NAME
====

elbe-initvm - High Level Interface to the ELBE System. Allows one to
create an initvm and directly build Rootfilesystems using ELBE.

SYNOPSIS
========

   ::

      elbe initvm [xmloptions] attach  [options]
      elbe initvm [xmloptions] create  [options] [<xmlfile> | <isoimage>]
      elbe initvm [xmloptions] submit  [options] [<xmlfile> | <isoimage>]
      elbe initvm [xmloptions] start   [options]
      elbe initvm [xmloptions] stop    [options]
      elbe initvm [xmloptions] ensure  [options]
      elbe initvm [xmloptions] destroy [options]

DESCRIPTION
===========

This command allows one to build and manage an initvm.

Initvms are managed via libvirt, and it’s necessary that a user is a
member of the libvirt group.

OPTIONS
=======

--directory <dir>
   Directory where the initvm resides, or is supposed to reside.
   (Defaults to *./initvm*)

--cdrom <CDROM>
   ISO image of Binary cdrom.

--skip-download
   After the build has finished, the generated Files are downloaded from
   the initvm to the host. This step is skipped, when this option is
   specified.

--output <dir>
   Directoryname where the generated and downloaded Files should be
   saved. The default is to generate a directory with a timestamp in the
   current working directory.

--skip-build-bin
   Skip building binary repository CDROM, for exact reproduction.

--skip-build-sources
   Skip building source CDROM.

--keep-files
   Don’t delete elbe project files after a build in the initvm use *elbe
   control list_projects* to get a list of available projects

--writeproject <file>
   Write project name to <file>.

--build-sdk
   Also make *initvm submit* build an SDK.

--qemu
   Use QEMU directly instead of libvirt.

XML OPTIONS
===========

--variant <variant>
   comma separated list of variants

--proxy <proxy>
   add proxy to mirrors

COMMANDS
========

*attach*
   Attach to the initvm console, which is accessed via virsh.

   User *root*, password *root*.

*create* [ <xmlfile> \| <isoimage> ]
   This command triggers a complete rebuild of the Elbe XML File. It
   also includes rebuilding the initvm.

   If an initvm is already available, you should use the *submit*
   command, to build a project in an existing initvm.

   Note that only a single initvm can be running on your host.

   When an iso Image with the binaries has been built earlier, it can
   also be used to recreate the original image. The source.xml from the
   iso will be used, and all the binary packages available also.

*submit* [ <xmlfile> \| <isoimage> ]
   This command triggers a complete rebuild of the Elbe XML File. It
   will however use an existing initvm.

   When an iso Image with the binaries has been built earlier, it can
   also be used to recreate the original image. The source.xml from the
   iso will be used, and all the binary packages available also.

*start*
   Start initvm in the Background.

*stop*
   Shutdown running initvm.

*sync*
   Upload elbe Version from the current working into initvm using rsync.
   Before using this command, you’ll have to add your client SSH key to
   */root/.ssh/authorized_keys* in initvm manually.

*ensure*
   Make sure an initvm is running in the Background.

*destroy*
   Clean up resources used by the initvm. initvm should be stopped before.

Examples
========

-  Build an initvm and on that build an elbe example:

   ::

      $ elbe initvm create /usr/share/doc/elbe-doc/examples/rescue.xml

-  Reuse the initvm built in the previous Step to build another example
   xml

   ::

      $ elbe initvm submit /usr/share/doc/elbe-doc/examples/elbe-desktop.xml

SEE ALSO
========

``elbe-control(1)``

ELBE
====

Part of the ``elbe(1)`` suite
