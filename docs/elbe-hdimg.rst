************************
elbe-hdimg
************************

.. _`_name`:

NAME
====

elbe-hdimg - Create hard disk and flash images from the given XML file.

.. _`_synopsis`:

SYNOPSIS
========

   ::

      elbe hdimg --target <dir> --output <out> \
              [ --buildtype <type> ] \
              [ --skip-validation ] \
              [ --skip-grub ] \
              <xmlfile>

.. _`_description`:

DESCRIPTION
===========

*elbe hdimg* creates hard disk and flash images from the *images*
section in the given XML file. The command has to be run as root
**inside the Elbe build VM**.

.. _`_options`:

OPTIONS
=======

--target <dir>
   Operate on the given project directory.

--output <out>
   Name of the log file.

--buildtype <type>
   Override the build type specified in the XML file.

--skip-validation
   Do not validate the XML file against the Elbe XML schema (Not
   recommended).

--skip-grub
   Skip GRUB installation.

<xmlfile>
   The XML file to use.

.. _`_examples`:

EXAMPLES
========

-  Build images for the project in */root/myproject*

   ::

      elbe hdimg --target /root/myproject --output /root/hdimg.log \
              /root/myproject/source.xml

.. _`_elbe`:

ELBE
====

Part of the ``elbe(1)`` suite
