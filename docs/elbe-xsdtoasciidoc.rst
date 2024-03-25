************************
elbe-xsdtoasciidoc
************************

.. _`_name`:

NAME
====

elbe-xsdtoasciidoc - Create an asciidoc documentation from an annotated
XML Schema file (xsd).

.. _`_synopsis`:

SYNOPSIS
========

   ::

      elbe xsdtoasciidoc [options] <xmlfile>

.. _`_description`:

DESCRIPTION
===========

This command generates documentation for the format of any ELBE XML
file. It parses the ELBE schema file and creates an asciidoc
documentation out of the annotations in the xsd file.

.. _`_options`:

OPTIONS
=======

--output=FILE specify output filename

<xsdfile>
   The xsdfile to be used.

.. _`_examples`:

EXAMPLES
========

-  get the documentation of the elbe xml format

   ::

      $ elbe xsdtoasciidoc /usr/share/elbe/dbsfed.xsd

.. _`_elbe`:

ELBE
====

Part of the ``elbe(1)`` suite
