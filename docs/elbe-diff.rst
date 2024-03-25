************************
elbe-diff
************************

.. _`_name`:

NAME
====

elbe-diff - Looks at 2 directories and makes Suggestions to modify the
xml file.

.. _`_synopsis`:

SYNOPSIS
========

   ::

      elbe diff <generated_dir> <fixed_dir>

.. _`_description`:

DESCRIPTION
===========

This command is useful, when the initially generated RootFS needs some
tweaks. It is supplied with the generated and the fixed rootfs, and will
suggest a finetuning section and a commandline to generate an archive
file.

.. _`_options`:

OPTIONS
=======

<generated_dir>
   This should point to the originally generated directory.

<fixed_dir>
   This should point to the fixed directory.

.. _`_elbe`:

ELBE
====

Part of the ``elbe(1)`` suite
