************************
elbe-repodir
************************

NAME
====

elbe-repodir - preprocesses and hosts repodirs on an Elbe client

SYNOPSIS
========

   ::

      'elbe repodir [options] <xmlfile>

DESCRIPTION
===========

elbe repodir preprocesses an XML file to convert <repodir> tags to valid
<url> tags. It runs a web server on a random TCP port with the root set
to a repodir’s PATH, which can be a relative path to the XML file or an
absolute filesystem path.

The repository is not considered to be signed unless the repodir
contains a signed-by attribute, which will then copy the given
ascii-armored OpenPGP keyring file as <raw-key> to the <url> node. The
key file must be a relative path to repodir’s PATH.

After the output file is written, the started webserver(s) will log
their accessed files.

OPTIONS
=======

--output <filename>
   preprocessed output file, defaults to repodir.xml. If this exists it
   will be overridden.

EXAMPLES
========

The source …

.. code:: xml

   <repodir>PATH1 bullseye main contrib</repodir>
   <repodir signed-by="relative-path.asc">PATH2 buster main</repodir>

i. is preprocessed to:

.. code:: xml

   <url>
     <binary>http://LOCALMACHINE:36071 bullseye main contrib</binary>
     <source>http://LOCALMACHINE:36071 bullseye main contrib</source>
     <options>
       <option>trusted=yes</option>
     </options>
   </url>
   <url>
     <binary>http://LOCALMACHINE:33187 buster main</binary>
     <source>http://LOCALMACHINE:33187 buster main</source>
     <raw-key>
       CONTENT OF KEYRING FILE "PATH2/relative-path.asc"
     </raw-key>
   </url>

i. with randomly chosen TCP port 36071 serving PATH1 and port 33187
   serving PATH2.

ELBE
====

Part of the ``elbe(1)`` suite
