************************
elbe-get_archive
************************

.. _`_name`:

NAME
====

elbe-get_archive - Extract the archive from an xmlfile.

.. _`_synopsis`:

SYNOPSIS
========

   ::

      elbe get_archive <xmlfile> <archive>

.. _`_description`:

DESCRIPTION
===========

This command extracts the archive from an xml file. It will not
overwrite anything.

.. _`_options`:

OPTIONS
=======

<xmlfile>
   The xml file to use.

<archive>
   Name of the extracted archive file. The archive must be a tar.bz2.

.. _`_examples`:

EXAMPLES
========

-  Extract the archive in *project.xml* to *archive.tar.bz2*

   ::

      $ elbe get_archive project.xml archive.tar.bz2

.. _`_elbe`:

ELBE
====

Part of the ``elbe(1)`` suite
