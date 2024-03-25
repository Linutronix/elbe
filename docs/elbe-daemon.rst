************************
elbe-daemon
************************

.. _`_name`:

NAME
====

elbe-daemon - control the ELBE daemon.

.. _`_synopsis`:

SYNOPSIS
========

   ::

      elbe daemon [options]

.. _`_description`:

DESCRIPTION
===========

This command controls the ELBE daemon and is run inside the inivm.

.. _`_options`:

OPTIONS
=======

--host <hostname>
   ip or hostname of the elbe-deamon (defaults to localhost, which is
   the default, where an initvm would be listening).

--port <N>
   Port of the soap interface on the elbe-daemon.

--<daemon>
   Enable <daemon>.

.. _`_elbe`:

ELBE
====

Part of the ``elbe(1)`` suite
