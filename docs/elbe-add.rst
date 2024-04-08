************************
elbe-add
************************

NAME
====

elbe-add - Insert new package(s) into the target package list.

SYNOPSIS
========

   ::

      elbe add [options] <xmlfile> <package name> [<package name>]*

DESCRIPTION
===========

This command adds an entry to the target pkg-list of the given XML file.
If more than one package name was given, all the packages are added to
the list. If a package already exists in the list, the package isn’t
added twice.

OPTIONS
=======

<xmlfile>
   The xmlfile to be modified.

EXAMPLES
========

-  Add *vim-nox* and *mc* into *mybsp.xml*

   ::

      $ elbe add mybsp.xml vim-nox mc

ELBE
====

Part of the ``elbe(1)`` suite
