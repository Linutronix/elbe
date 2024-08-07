************************
elbe-pbuilder
************************

NAME
====

elbe-pbuilder - High Level Interface to the ELBE Package Build System.
Allows one to create a package builder for a project and to build Debian
packages.

SYNOPSIS
========

   ::

      elbe pbuilder build  [--project <project> | --xmlfile <xmlfile>]
      elbe pbuilder create [--project <project> | --xmlfile <xmlfile>] [--writeproject <filename>]

DESCRIPTION
===========

Creates a pbuilder for a specified project and builds the Debian package
like pbuilder, but for the configured ELBE project.

OPTIONS
=======

--project <dir>
   *key* (/var/cache/elbe/<uuid> for the project inside the initvm to
   use. Use *elbe control list_projects* to get a list of the available
   projects. Another option would be to use the --writeproject option,
   when the pbuilder is created.

--xmlfile <xmlfile>
   This file is used to create a new ELBE project including the pbuilder
   environment.

--profile string
   Specify the build profile(s) to build. (dpkg-buildpackage
   -P<profile>) Provide multiple profiles as a comma separated list.

--cross
   Combined with the create command it creates a chroot environment to
   make crossbuilding possible. Combined with the build command it will
   use this environment for crossbuilding.

--no-ccache
   The compiler cache *ccache* is activated by default. Use this option
   with the *create* command to deactivate it.

--ccache-size <string>
   Use this option to configure the limit of the compiler cache. Should
   be a number followed by an optional suffix: k, M, G, T. Use 0 for no
   limit.

XML OPTIONS
===========

--variant <variant>
   comma separated list of variants

--proxy <proxy>
   add proxy to mirrors

COMMANDS
========

*create*
   A pbuilder environment for the given project or xml File will be
   created. If --cross is given the pbuilder environment will be created
   to crossbuild packages. (If --cross is given with the create command
   you have to use --cross with the build command also.) The compiler
   cache ``ccache`` gets installed by default to speed up
   recompilations. To deactivate use ``--no-ccache`` with the create
   command. It is possible to change the size with
   ``--ccache-size <string>`` where string should be a number followed
   by an optional suffix: k, M, G, T. For no limit use 0.

*build*
   Build the *Debianized Project* in the current working directory. (A
   valid ./debian directory needs to exist.) If --project was specified,
   the specified build environment will be used. If --xmlfile is
   specified, a new build environment will be created for the given ELBE
   XML File, and the *Debianized Project* in the current working
   directory will be built. The result of the package build is stored in
   ../ like pbuilder does.

NOTES
=====

In this benchmark all opportunitys for creating a pbuilder environment
and building a package with it were tested. All environments were
created with the *armhf-ti-beaglebone-black.xml* example and with cross,
ccache, no-cross or no-ccache in all possible variations. The build
command was tested with the zlib package. All times are real-time
captures. The build command with ccache was tested twice to see the
impact of ccache.

pbuilder no-ccache create 6m35,003s pbuilder no-ccache build 7m19,467s

pbuilder no-ccache cross create 4m2,553s pbuilder no-ccache build
2m39,151s

pbuilder ccache create 6m44,117s pbuilder ccache build 1. 7m36,130s 2.
4m47,050s

pbuilder ccache cross create 4m4,190s pbuilder ccache cross build 1.
2m40,159s 2. 2m32,650s

EXAMPLES
========

-  Build a pbuilder for *myarm.xml*. Save project name into myarm.prj

   ::

      # elbe pbuilder create --xmlfile myarm.xml --writeproject myarm.prj

-  Use the pbuilder we have built, to build *program*, using the prj
   File generated in parent directory

   ::

      # cd program
      # elbe pbuilder build --project `cat ../myarm.prj`

-  Use the pbuilder we have built, to build *program*, using the prj
   File generated in parent directory. And don’t use more than one CPU
   as a workaround for qemu-user and java problems.

   ::

      # cd program
      # elbe pbuilder build --project `cat ../myarm.prj`

SEE ALSO
========

``elbe-control(1)`` ``elbe-initvm(1)`` ``pdebuild(1)``

ELBE
====

Part of the ``elbe(1)`` suite
