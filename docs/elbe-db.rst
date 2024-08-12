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
      elbe db [options] list_users
      elbe db [options] save_version <project_dir>
      elbe db [options] set_xml <project_dir> <xml_file>
      elbe db [options] del_project <project_dir>
      elbe db [options] init
      elbe db [options] del_user <userid>
      elbe db [options] add_user <username>
      elbe db [options] list_versions <project_dir>
      elbe db [options] del_versions <project_dir> <version>
      elbe db [options] build <project_dir>

DESCRIPTION
===========

This command controls the ELBE daemon and is run inside the initvm.

OPTIONS
=======

-h, --help
   Displays help.

--name
   Sets the name of the new user.

--fullname
   Sets the full name of the new user.

--password
   Sets the password of the new user.

--email
   Sets the email address of the new user.

--noadmin
   TODO!! MACHT MEINER MEINUNG NACH DAS GLEICHE WIE ADMIN.

--admin
   Gives the new user admin privileges. (Boolean variable,
   default=False).

--delete-projects
   Delete all projects owned by the user.

--quiet
   TODO

--user
   User name of the project owner.

--clean
   Deletes the target and chroot directory in <project-dir>.

--description
   Description of the project version which shall be stored in the
   database.

COMMANDS
========

*init*
   Creates a new ELBE database and adds one new user. Options:
   name[=root], fullname[=Admin], password[=foo],
   email[=\ root@localhost], noadmin[=True].

*add_user* <username>
   Adds a new user. Options: fullname, password, email, admin=[False].

*del_user* <userid>
   Deletes user <userid>. Options: delete-projects[=False],
   quiet=[False].

*list_projects*
   Lists all projects stored in the database.

*list_users*
   Lists all users registered in the ELBE database.

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

*list_versions* <project_dir>
   Lists all versions of project <project_dir>.

*save_version* <project_dir>
   Saves current state of project <project_dir> as version. Options:
   description.

*del_versions* <project_dir> <version>
   Deletes the version <version> of project <project_dir>.

ELBE
====

Part of the ``elbe(1)`` suite
