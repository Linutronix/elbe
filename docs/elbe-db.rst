************************
elbe-db
************************

NAME
====

elbe-db - interface to the ELBE db. Must be run inside the initvm.

SYNOPSIS
========

   ::

      elbe db [options] list_projects
      elbe db [options] create_project <project_dir>
      elbe db [options] get_files <project_dir>
      elbe db [options] reset_project <project_dir>
      elbe db [options] set_xml <project_dir> <xml_file>
      elbe db [options] del_project <project_dir>
      elbe db [options] init
      elbe db [options] build <project_dir>

DESCRIPTION
===========

This command controls the ELBE daemon and is run inside the initvm.

OPTIONS
=======

-h, --help
   Displays help.

--clean
   Deletes the target and chroot directory in <project-dir>.

COMMANDS
========

*init*
   Creates a new ELBE database and adds one new user. Options:
   name[=root], fullname[=Admin], password[=foo],
   email[=\ root@localhost], noadmin[=True].

*list_projects*
   Lists all projects stored in the database.

*create_project* <project_dir>
   Creates a new project in directory <project_dir>. Options: user.

*del_project* <project_dir>
   Removes project in <project_dir> from ELBE database.

*set_xml* <project_dir> <xml_file>
   Assigns the file <xml_file> as ELBE recipe to the project in
   <project_dir>.

*build* <project_dir>
   Builds the project in <project_dir>.

*get_files* <project_dir>
   Returns a list of all files and directories in <project_dir>

*reset_project* <project_dir>
   Resets the project state in the database. Can be useful if a build
   has been aborted and the project is set ``busy`` in in the database
   obstructing future actions on this project. Options: clean[=False].

ELBE
====

Part of the ``elbe(1)`` suite
