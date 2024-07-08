************************
elbe
************************

NAME
====

elbe - Embedded Linux Build Environment

SYNOPSIS
========

   ::

      elbe <command> [<args>]

DESCRIPTION
===========

Elbe is a system to build Rootfilesystems from XML description files. It
also includes tools to modify xml files.

The *<command>* is a name of an Elbe command (see below).

Elbe COMMANDS
=============

``elbe-initvm(1)``
   build and manage initvm. Also allows one to submit xml Files into the
   initvm

``elbe-control(1)``
   low-level interface to projects inside the initvm.

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

``elbe-get_archive(1)``
   extract a config archive (.tbz) from a XML file.

``elbe-init(1)``
   create a project for an Elbe build virtual machine.

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

SEE ALSO
========

``elbe(1)``

ELBE
====

Part of the ``elbe(1)`` suite
