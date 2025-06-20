************************
elbe-control
************************

NAME
====

elbe-control - Low level interface to elbe Soap Daemon running in initvm

SYNOPSIS
========

   ::

      elbe control [options] list_projects
      elbe control [options] create_project
      elbe control [options] build_sysroot <build-dir>
      elbe control [options] build_cdroms <build-dir>
      elbe control [options] set_pdebuild <project-dir> <pdebuild file>
      elbe control [options] get_files <build-dir>
      elbe control [options] build_chroot_tarball <build-dir>
      elbe control [options] build_sdk <build-dir>
      elbe control [options] set_orig <build-dir>
      elbe control [options] set_cdrom <build-dir> <iso-img>
      elbe control [options] reset_project <build-dir>
      elbe control [options] wait_busy <build-dir>
      elbe control [options] set_xml <build-dir> <xmlfile>
      elbe control [options] del_project <build-dir>
      elbe control [options] del_all_projects
      elbe control [options] build_pbuilder <build-dir>
      elbe control [options] build <build-dir>
      elbe control [options] rm_log <build-dir>
      elbe control [options] get_file <build-dir> <filename>
      elbe control [options] dump_file <build-dir> <filename>

DESCRIPTION
===========

Low Level interface to control an elbe daemon running inside an initvm.
It allows one to submit xml files etc.

For the high level interface, see *elbe initvm*

Please take notice, that a single user can only have a single project
opened inside the soap server. So it is not possible to have a single
user build 2 projects at once.

You can only wait on the project, that you are currently building.

OPTIONS
=======

--host <hostname>
   ip or hostname of the elbe-deamon (defaults to localhost, which is
   the default, where an initvm would be listening).

--port <N>
   Port of the soap interface on the elbe-daemon.

--user <username>
   Username to use for login (defaults to root).

--pass <password>
   Password for login (defaults to *foo*).

--retries <N>
   How many times to retry the connection to the server before giving up
   (default is 10 times, yielding 10 seconds).

--build-bin
   Build binary repository CDROM, for exact reproduction.

--build-sources
   Build source CDROM.

--output <directory>
   Output downloaded files to <directory>.

--pbuilder-only
   Only list/download pbuilder files.

--profile
   Specify pbuilder profile(s) to build. Provide multiple profiles as a
   comma separated list.

COMMANDS
========

*list_projects*
   List projects available on the elbe daemon.

*create_project*
   Create a new project on soap server. a new build-dir is created.

   The name of the created <build-dir> is printed to stdout, for further
   reference in subsequent commands.

*build_sysroot* <build-dir>
   Build a sysroot for the specified project.

The sysroot can be used with a toolchain for cross-compiles.

*build_cdroms* <build-dir>
   Build ISO images containing the Debian binary or source packages used
   by the given build-dir. Either --build-bin or --build-sources or both
   needs to be specified.

*set_pdebuild* <build-dir> <pdebuild file>

Build a Debian Project using a pbuilder.

The pdebuild file needs to be a .tar.gz archive of a project containing
a ./debian folder with a valid debianization.

+ The generated debian packages are stored inside the initvm.

+ Use get_files to retrieve them.

*get_files* <build-dir>
   Get list of files in the <build-dir>.

   If the --output option is specified, the files are downloaded to the
   directory specified in the option. If the --matches option is
   specified only files matching the wildcard expression are
   shown/downloaded. Note that you have to put the wildcard expression
   in quotation marks.

*build_chroot_tarball* <build-dir>
   Creates a tarball of the chroot environment in <build_dir>.

*build_sdk* <build-dir>
   Creates a yocto-style SDK.

*set_orig* <build-dir> <orig-file>
   Uploads a quilt orig-file to the initvm.

   This command shall be run before building a Debian package with
   ``elbe pbuilder build`` if the package is given in the quilt source
   format.

*set_cdrom* <build-dir> <iso-img>
   Set the cdrom iso image. The <iso-img> is uploaded into the intivm.
   And the source.xml in the <build-dir> is modified, that it builds
   from the cdrom mirror now.

*reset_project* <build-dir>
   Reset project database status for <build-dir>.

   When the database becomes inconsistent, this allows us to access an
   otherwise blocked project again.

   Use with care.

*wait_busy* <build-dir>
   Wait, while <build-dir> is busy.

*set_xml* <build-dir> <xmlfile>
   Upload a new xml File into the given <build-dir>. This is most likely
   going to change the status of the project to *needs_rebuild*.

*del_project* <build-dir>
   Delete project in <build-dir>

*del_all_projects*
   Delete all projects

*build_pbuilder* <build-dir>
   Build a pbuilder environment for the given project <build-dir>.

*build* <build-dir>
   Trigger building the project. Status will change to busy.

*rm_log* <build-dir>
   Deletes log file for the given project <build-dir>

*get_file* <build-dir> <filename>
   Download a single file from the project.

*dump_file* <build-dir> <filename>
   Dump a single File from the project to stdout.

Examples
========

-  List current Projects

   ::

      $ elbe control list_projects
      /var/cache/elbe/982d64de-e69f-48c7-8942-66d8d480f3dc    rescue image    1.0     build_done      2015-06-08 15:29:29.613620
      /var/cache/elbe/dd37a03e-31bd-45db-afd4-fc51d51fa90a    rescue image    1.0     build_done      2015-06-09 08:53:26.658500
      /var/cache/elbe/8d62928f-4e75-47cf-aec9-d2365ca59003    rescue image    1.0     build_done      2015-06-09 09:14:15.371456

-  Create a new Project, trigger build, and wait till it finishes.

   ::

      $ elbe control create_project examples/rescue.xml
      /var/cache/elbe/f310dcbc-f5fc-423e-99e4-fb72d7b9dd5f
      $ elbe control build /var/cache/elbe/f310dcbc-f5fc-423e-99e4-fb72d7b9dd5f
      $ elbe control wait_busy /var/cache/elbe/f310dcbc-f5fc-423e-99e4-fb72d7b9dd5f
      project still busy, waiting
      project still busy, waiting
      ...
      project still busy, waiting
      $ elbe control get_files /var/cache/elbe/f310dcbc-f5fc-423e-99e4-fb72d7b9dd5f
      source.xml      (Current source.xml of the project)
      rescue.cpio     (Image)
      validation.txt  (Package list validation result)
      elbe-report.txt         (Report)
      log.txt         (Log file)

SEE ALSO
========

``elbe-initvm(1)`` ``git-daemon(1)``

ELBE
====

Part of the ``elbe(1)`` suite
