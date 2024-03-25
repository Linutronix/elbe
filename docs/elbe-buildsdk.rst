************************
elbe-buildsdk
************************

.. _`_name`:

NAME
====

elbe-buildsdk - Build a yocto style sdk.

.. _`_synopsis`:

SYNOPSIS
========

   ::

      elbe buildsdk <directory>

<directory>
   directory containing the elbe project.

.. _`_description`:

DESCRIPTION
===========

creates a yocto style SDK

.. _`_examples`:

EXAMPLES
========

-  Build a root filesystem from *myarm.xml* in */root/myarm*. Log to
   *myarm.txt*. Then create a SDK for this RFS.

   ::

      # elbe buildchroot --output myarm.txt --target /root/myarm myarm.xml
      # elbe buildsdk /root/myarm

.. _`_elbe`:

ELBE
====

Part of the ``elbe(1)`` suite
