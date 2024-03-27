************************
elbe
************************

.. _`_name`:

NAME
====

elbe - Embedded Linux Build Environment

.. _`_synopsis`:

SYNOPSIS
========

   ::

      elbe <command> [<args>]

.. _`_description`:

DESCRIPTION
===========

Elbe is a system to build Rootfilesystems from XML description files. It
also includes tools to modify xml files.

The *<command>* is a name of an Elbe command (see below).

.. _`_elbe_commands`:

Elbe COMMANDS
=============

``elbe-initvm(1)``
   build and manage initvm. Also allows one to submit xml Files into the
   initvm

``elbe-control(1)``
   low-level interface to projects inside the initvm.

``elbe-buildchroot(1)``
   build a root filesystem.

``elbe-buildsysroot(1)``
   build a sysroot archive.

``elbe-check_updates(1)``
   check whether package updates are available for a given project.

``elbe-chg_archive(1)``
   insert a new config archive (.tbz) into a XML file.

``elbe-chroot(1)``
   enter a root filesystem with chroot.

``elbe-diff(1)``
   compare two root file systems for differing files.

``elbe-gen_update(1)``
   generate an update archive for elbe-updated.

``elbe-genlicence(1)``
   generate a file containing the licences of all packages included in a
   project.

``elbe-get_archive(1)``
   extract a config archive (.tbz) from a XML file.

``elbe-hdimg(1)``
   create a hard disk image from the given XML file.

``elbe-init(1)``
   create a project for an Elbe build virtual machine.

``elbe-mkcdrom(1)``
   create an ISO image containing all binary or source packages used in
   the given project.

``elbe-pbuilder(1)``
   generate a pbuilder environment and build packages within it

``elbe-pkgdiff(1)``
   compare two root filesystems for differing packages.

``elbe-remove_sign(1)``
   verify a signed file and remove the signature.

``elbe-setsel(1)``
   update the packagelist from the output of dpkg-getselections.

``elbe-show(1)``
   show a textual information about the given XML file.

``elbe-sign(1)``
   add a signature to the given file.

``elbe-updated(1)``
   start the Elbe update daemon.

``elbe-validate(1)``
   validate the given XML file against the Elbe XML Schema.

.. _`_see_also`:

SEE ALSO
========

``elbe(1)``

.. _`_elbe`:

ELBE
====

Part of the ``elbe(1)`` suite
