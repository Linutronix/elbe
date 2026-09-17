****************
elbe check-build
****************

NAME
====

elbe check-build - Test various aspects of the build output.

SYNOPSIS
========

   ::

      elbe check-build {all,schema,cdrom,img,sdk,rebuild} <build_dir>

DESCRIPTION
===========

This command runs tests for various aspects of the build output.

OPTIONS
=======

{all,schema,cdrom,img,sdk,rebuild}
   What aspect to test, or all of them.

<build_dir>
   The build directory where the output artefacts are (e.g. the image file and packages).

IMAGE TESTING
=============

The ``img`` sub-command tests the actual target image. ``elbe check-build img`` looks in
the original image definition xml for two definitions:

 - how to boot test the image with a QEMU command-line embedded in the XML

 - how to run a check script on the build directory.

An example of both can be seen in ``tests/simple-validation-image.xml``:

.. literalinclude:: ../tests/simple-validation-image.xml
   :language: xml
   :start-at: <check-image-list>
   :end-at: </check-image-list>
   :dedent:

You can run ``check-build`` to test an image like this if you have a
ready build directory with it::

  $ elbe check-build img <path/to/build/dir>

If the image xml contained something like the example above, it will
first boot the image and check that root login works, then run the
``simple-validation-image-test.py`` script.


EXAMPLES
========

-  Test the content of the image:

   ::

      $ elbe check-build img <path/to/build/dir>

ELBE
====

Part of the ``elbe(1)`` suite
