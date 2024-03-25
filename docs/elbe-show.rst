************************
elbe-show
************************

.. _`_name`:

NAME
====

elbe-show - Get a human readable representation of a ELBE XML file.

.. _`_synopsis`:

SYNOPSIS
========

   ::

      elbe show [--verbose] <xmlfile>

.. _`_description`:

DESCRIPTION
===========

This command generates a human readable overview of a given ELBE XML
file.

It’s useful to get an idea what a specific XML file was designed for.

.. _`_options`:

OPTIONS
=======

--verbose
   Give more information, e.g. the package list of the target
   root-filesystem.

<xmlfile>
   The xmlfile to be shown.

.. _`_examples`:

EXAMPLES
========

-  get a human readable representation of *project.xml*

   ::

      $ elbe show project.xml

.. _`_elbe`:

ELBE
====

Part of the ``elbe(1)`` suite
