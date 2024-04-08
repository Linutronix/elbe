************************
elbe-setsel
************************

NAME
====

elbe-setsel - Replace the package list of an Elbe XML file by a list
obtained from *dpkg-getselections*.

SYNOPSIS
========

   ::

      elbe setsel <xmlfile> <pkglist>

DESCRIPTION
===========

*elbe setsel* replaces the package list of an Elbe XML file by a package
list obtained from *dpkg --get-selections*. Together with the setsel
mode of Elbe, this offers a more fine-grained control on which packages
are installed (even apt and aptitude can be excluded from the root
filesystem). The recommended usage is as follows:

1. Generate an image using the default mode of Elbe.

2. Run the image and use *apt-get* to purge unwanted packages.

3. Maybe even use *dpkg* to remove apt and aptitude.

4. Generate the list of selected packages using *dpkg --get-selections >
   selections.list*

5. Transfer this file to the host system.

6. Use *elbe setsel <xmlfile> selections.list* to import the package
   list into the XML file.

7. Rebuild using the setsel mode of Elbe.

OPTIONS
=======

<xmlfile>
   The XML file to modify.

<pkglist>
   The package list from *dpkg --get-selections*.

EXAMPLES
========

-  Replace the package list of myproject.xml with the packages listed by
   *dpkg --get-selections > myproject.pkgs*.

   ::

      $ elbe setsel myproject.xml myproject.pkgs

ELBE
====

Part of the ``elbe(1)`` suite
