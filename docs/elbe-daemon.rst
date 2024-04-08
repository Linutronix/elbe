************************
elbe-daemon
************************

NAME
====

elbe-daemon - control the ELBE daemon.

SYNOPSIS
========

   ::

      elbe daemon [options]

DESCRIPTION
===========

This command controls the ELBE daemon and is run inside the inivm.

OPTIONS
=======

--host <hostname>
   ip or hostname of the elbe-deamon (defaults to localhost, which is
   the default, where an initvm would be listening).

--port <N>
   Port of the soap interface on the elbe-daemon.

--<daemon>
   Enable <daemon>.

ELBE
====

Part of the ``elbe(1)`` suite
