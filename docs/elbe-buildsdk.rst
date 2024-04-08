************************
elbe-buildsdk
************************

NAME
====

elbe-buildsdk - Build a yocto style sdk.

SYNOPSIS
========

   ::

      elbe buildsdk <directory>

<directory>
   directory containing the elbe project.

DESCRIPTION
===========

creates a yocto style SDK

EXAMPLES
========

-  Build a root filesystem from *myarm.xml* in */root/myarm*. Log to
   *myarm.txt*. Then create a SDK for this RFS.

   ::

      # elbe buildchroot --output myarm.txt --target /root/myarm myarm.xml
      # elbe buildsdk /root/myarm

ELBE
====

Part of the ``elbe(1)`` suite
