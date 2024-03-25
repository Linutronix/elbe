************************
elbe-prjrepo
************************

.. _`_name`:

NAME
====

elbe-prjrepo - Provides access to the Debian repositories in each
project folder.

.. _`_synopsis`:

SYNOPSIS
========

   ::

      elbe prjrepo download <project_dir>
      elbe prjrepo upload_pkg <project_dir> [<debfile> | <dscfile> | <changesfile>]
      elbe prjrepo list_packages <project_dir>

.. _`_description`:

DESCRIPTION
===========

Whenever ELBE pbuilder builds a Debian package, it is added to a local
Debian repository which is located in the project folder inside the
initvm. Packages in this repository can then be installed into a root
file system. The ``elbe-prjrepo`` command allows the user to interact
with this repository, i.e. list, upload and download packages.

.. _`_options`:

OPTIONS
=======

--user <username>
   Username to use for login (defaults to root).

--pass <password>
   Password for login (defaults to *foo*).

--retries <N>
   How many times to retry the connection to the server before giving up
   (default is 10 times, yielding 10 seconds).

.. _`_commands`:

COMMANDS
========

*download* <project_dir>
   Downloads the Debian repository of the project located in
   <project_dir> to the host machine.

*upload_pkg* <project_dir> [<debfile> \| <dscfile> \| <changesfile>]
   Loads a Debian package into the Debian repository of an existing Elbe
   project in the initvm. Both binary and source packages are supported.
   In order to upload a source package you need to specify the dsc-file
   in the command as shown above. The actual source files which are
   required for the source package need to be located in the same
   directory as the dsc-file. The same is true for a changes file. The
   actual files defined in the changes file need to reside in the same
   directory.

*list_packages* <project_dir>
   Lists all packages available in the Debian repository of the project.

.. _`_example`:

Example
=======

-  List the packages available in the project
   38599ce2-4cad-4578-bfe1-06fa793b883a:

   ::

      $ elbe prjrepo list_packages "/var/cache/elbe/38599ce2-4cad-4578-bfe1-06fa793b883a"

.. _`_elbe`:

ELBE
====

Part of the ``elbe(1)`` suite
