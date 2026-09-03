************
ELBE testing
************

.. _`_overview`:

Overview
========

Elbe testing is performed with pytest framework:
https://docs.pytest.org/en/stable/

To run a ’fast’ subset of the tests you can execute ``pytest`` directly
from the top level source directory. It will take about 30 seconds.

One important test in the ’fast’ subset is
``elbepack/tests/test_flake8.py`` which checks python code for style
consistency. It is common in ongoing development to violate style rules
(e.g. regarding indentation or use of quotes), and it’s strongly
recommended to make sure that test doesn’t complain before submitting
code changes for review.

To see a complete list of possible tests, run ``pytest --collect-only``. The
list includes both fast and slow tests. In theory, you can run the full
set with ``pytest --runslow`` but that is not recommended in local
development as it will take many hours. It’s better to run particular
relevant slow tests, for example::

  $ pytest -s -k "test_base_extended_build[simple-validation-image.xml]" --runslow --elbe-use-initvm=existing

.. note::
   ``--elbe-use-initvm`` tells pytest what initvm to use for the purpose of making images.
   There are three possible values for the argument:

   * ``existing`` simply reuses an existing initvm, and runs ``elbe submit`` and other commands without creating an initvm first.
     This is recommended for local development and testing.

   * ``libvirt`` will run ``elbe initvm create`` before the tests and ``initvm stop``/``initvm destroy`` afterwards, which will
     produce an entirely new initvm.

   * ``qemu`` will additionally pass in ``--qemu`` argument to ``create``/``stop``/``destroy`` commands.

   See :doc:`elbe-initvm`  for more information about ``elbe initvm`` command.

.. _`_important:_what_to_do_if_you_see_weird_out_of_memory_errors`:

Important: what to do if you see weird out of memory errors
-----------------------------------------------------------

By default, pytest sets up output in ``/tmp``. This includes any ELBE images
and other build artifacts, which can run up to many gigabytes in size,
especially after consecutive pytest invocations which keep several last
outputs for inspection. The problem comes when /tmp is mounted not into
a real disk space, but using tmpfs in RAM (for example, Debian and
Fedora do it): writing into /tmp directly consumes RAM, and when it’s
exhausted, OOM mechanisms of the host distribution will kick in and
terminate processes in a vain attempt to recover memory.

To redirect output to somewhere else, use the ``--basetemp`` option::

  $ pytest --basetemp=$HOME/elbe-tests/

Note that this directory would be wiped clean by pytest, so do not pass
in $HOME or other important locations. See
https://docs.pytest.org/en/stable/how-to/tmp_path.html#temporary-directory-location-and-retention
for details.

.. _`_image_testing`:

Image testing
=============

This is a multi-layer process with several levels of abstraction.

.. _`_pytest_based_top_level_tests`:

Pytest based top level tests
----------------------------

On the top level, there are pytest test cases, defined in
``elbepack/tests/test_xml.py``.

They’re visible in list of tests provided by ``pytest --collect-only``:

::

   <Function test_simple_build[simple-validation-image.xml-schema]>
   <Function test_simple_build[simple-validation-image.xml-cdrom]>
   <Function test_simple_build[simple-validation-image.xml-img]>
   <Function test_simple_build[simple-validation-image.xml-sdk]>
   <Function test_rebuild[simple-validation-image.xml]>
   <Function test_check_updates[simple-validation-image.xml]>
   <Function test_base_extended_build[simple-validation-image.xml]>

The same set of tests is provided for every ``tests/simple-*.xml`` image.
Of particular interest is the test_simple_build case that has four
variants, each of which runs ``elbe check-build <variant>``:

.. literalinclude:: ../elbepack/tests/test_xml.py
   :language: python
   :pyobject: test_simple_build

.. _`_what_does_elbe_check_build_do?`:

What does ``elbe check-build`` do?
--------------------------------------

Please refer to :doc:`elbe-check-build`.

.. _`_what_does_simple_validation_image_test_py_script_do?`:

What does simple-validation-image-test.py script do?
----------------------------------------------------

This script checks various aspects of the build output produced by
``tests/simple-validation-image.xml`` and extended images based on it
(currently there is one such image defined in
``tests/base-extended/simple-validation/image-extended.xml`` and tested in
pytest’s ``test_base_extended_build[test_base_extended_build]``).

It can handle both disk images (which are mounted using guestfs so that
the root filesystem can be inspected) and base image tarballs, which get
unpacked and similarly inspected. To run the script directly use::

  $ PYTHONPATH=. tests/simple-validation-image-test.py path/to/build/dir

.. _`_how_do_i_prepare_a_build_directory_in_the_examples_above?`:

How do I prepare a build directory in the examples above?
---------------------------------------------------------

Top level pytest handles everything and is fully self-contained: you can
run it without preparing any builds. The downside of that is that it
takes a long time to build an image and related artefacts (e.g. sdk),
and this isn’t suitable for iterative development.

In this case you should use ``elbe check-build`` or
``simple-validation-image-test.py`` script directly, as they only take a few
seconds if there is a ready build directory to run on.

Such a build directory can be produced using the standard ``elbe submit``
procedure::

  $ ./elbe --stacktrace-on-error initvm submit --skip-build-bin --skip-build-sources tests/simple-validation-image.xml

or to build an extended image using the base image output::

  $ ./elbe --stacktrace-on-error initvm submit --skip-build-bin --skip-build-sources --base-image ./elbe-build-20260903-110523/base-rootfs.tgz tests/base-extended/simple-validation/image-extended.xml

.. _`_tying_it_all_together`:

Tying it all together
---------------------

Here’s a chart of all the pieces in a hierarchy, so it’s clear what is
calling what::

	pytest
	  -> test_simple_build()
	     -> elbe check-build img
	        -> qemu boot login test defined in <check> section of simple-validation-image.xml
	        -> <check-script> from simple-validation-image.xml
	           -> run simple-validation-image-test.py
	              -> helper functions from elbevalidate python module

