************************
elbe-remove_sign
************************

.. _`_name`:

NAME
====

elbe-remove_sign - Verify a signed file and remove the signature.

.. _`_synopsis`:

SYNOPSIS
========

   ::

      elbe remove_sign <filename>

.. _`_description`:

DESCRIPTION
===========

This command checks the validity of a file signed with ``elbe-sign(1)``
or *gpg --sign*. It uses the GPG keyring of the current user, so for
this to work the public key of the signer has to be added to the
keyring. Note that to get *VALID (Trusted)*, the key has to have
ultimate trust.

.. _`_options`:

OPTIONS
=======

<filename>
   The name of the file to sign.

.. _`_examples`:

EXAMPLES
========

-  check validity of *rfs.tar.bz2.gpg* and remove the signature

   ::

      elbe remove_sign rfs.tar.bz2.gpg

.. _`_elbe`:

ELBE
====

Part of the ``elbe(1)`` suite
