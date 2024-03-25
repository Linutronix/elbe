************************
elbe-add
************************

.. _`_name`:

NAME
====

elbe-add - Insert new package(s) into the target package list.

.. _`_synopsis`:

SYNOPSIS
========

   ::

      elbe add [options] <xmlfile> <package name> [<package name>]*

.. _`_description`:

DESCRIPTION
===========

This command adds an entry to the target pkg-list of the given XML file.
If more than one package name was given, all the packages are added to
the list. If a package already exists in the list, the package isn’t
added twice.

.. _`_options`:

OPTIONS
=======

<xmlfile>
   The xmlfile to be modified.

.. _`_examples`:

EXAMPLES
========

-  Add *vim-nox* and *mc* into *mybsp.xml*

   ::

      $ elbe add mybsp.xml vim-nox mc

.. _`_elbe`:

ELBE
====

Part of the ``elbe(1)`` suite
