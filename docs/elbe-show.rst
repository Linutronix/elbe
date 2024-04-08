************************
elbe-show
************************

NAME
====

elbe-show - Get a human readable representation of a ELBE XML file.

SYNOPSIS
========

   ::

      elbe show [--verbose] <xmlfile>

DESCRIPTION
===========

This command generates a human readable overview of a given ELBE XML
file.

It’s useful to get an idea what a specific XML file was designed for.

OPTIONS
=======

--verbose
   Give more information, e.g. the package list of the target
   root-filesystem.

<xmlfile>
   The xmlfile to be shown.

EXAMPLES
========

-  get a human readable representation of *project.xml*

   ::

      $ elbe show project.xml

ELBE
====

Part of the ``elbe(1)`` suite
