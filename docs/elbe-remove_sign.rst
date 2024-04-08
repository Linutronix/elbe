************************
elbe-remove_sign
************************

NAME
====

elbe-remove_sign - Verify a signed file and remove the signature.

SYNOPSIS
========

   ::

      elbe remove_sign <filename>

DESCRIPTION
===========

This command checks the validity of a file signed with ``elbe-sign(1)``
or *gpg --sign*. It uses the GPG keyring of the current user, so for
this to work the public key of the signer has to be added to the
keyring. Note that to get *VALID (Trusted)*, the key has to have
ultimate trust.

OPTIONS
=======

<filename>
   The name of the file to sign.

EXAMPLES
========

-  check validity of *rfs.tar.bz2.gpg* and remove the signature

   ::

      elbe remove_sign rfs.tar.bz2.gpg

ELBE
====

Part of the ``elbe(1)`` suite
