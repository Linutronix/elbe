************************
elbe-sign
************************

.. _`_name`:

NAME
====

elbe-sign - Add a signature to the given file

.. _`_synopsis`:

SYNOPSIS
========

   ::

      elbe sign <filename> <fingerprint>

.. _`_description`:

DESCRIPTION
===========

Sign the given file with the GPG key having the specified fingerprint.
The resulting file will contain both the compressed data and the
signature (the same format *gpg --sign* uses if no other arguments are
specified), and it will get a *.gpg* extension.

The person receiving the file can use *gpg --decrypt* or
``elbe-remove_sign(1)`` to verify the file and to get the original
content.

.. _`_options`:

OPTIONS
=======

<filename>
   The name of the file to sign.

<fingerprint>
   The fingerprint of the private GPG key to use for signing the file.

.. _`_examples`:

EXAMPLES
========

-  sign *rfs.tar.bz2* with the key having the fingerprint *FEE1DEAD*

   ::

      elbe sign rfs.tar.bz2 FEE1DEAD

.. _`_elbe`:

ELBE
====

Part of the ``elbe(1)`` suite
