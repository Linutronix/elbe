************************
elbe-genlicence
************************

.. _`_name`:

NAME
====

elbe-genlicence - Generate a file containing the licences of the
packages included in a project.

.. _`_synopsis`:

SYNOPSIS
========

   ::

      elbe genlicence \
              [ --output <filename> ] \
              [ --xml <xmlfilename> ] \
              <project-dir>

.. _`_description`:

DESCRIPTION
===========

*elbe-genlicence* creates a file which will contain the licences of the
packages included in a project, generated from the *copyright* files in
the */usr/share/doc/\** directories of the root filesystem.

This command has to be run **inside the Elbe build VM**.

.. _`_options`:

OPTIONS
=======

--output <filename>
   Write the result to <filename> instead of *licence.txt*.

--xml <xmlfilename>
   Write an xml file with all the licenses to <xmlfilename>.

--buildtype <buildtype>
   Override the buildtype.

--skip-validation
   Skip xml schema validation.

<project>
   The build directory of the project to process.

.. _`_examples`:

EXAMPLES
========

-  Generate a licence file for the project in */var/cache/elbe/<uuid>*
   and name the result *myproject-licences.txt*.

   ::

      # elbe genlicence --output myproject-licences.txt /var/cache/elbe/<uuid>

.. _`_elbe`:

ELBE
====

Part of the ``elbe(1)`` suite
