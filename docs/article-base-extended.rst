**********************************************
Base images and extended images (experimental)
**********************************************

Typically building an ELBE image is entirely self-contained, and is done in a single step: packages are pulled in from Debian (or custom) repositories,
and are used to form a root filesystem.

With the base-extended image mechanism it is possible to first produce a 'base image': a packaged root filesystem that is then used as input to
producing an extended image. Instead of pulling packages, the base image is unpacked into the root filesystem directory and then further additions and adjustments
are perfomed to form the final output for the extended image. This development flow can be recursively extended further: an extended image can be used as a base
image for further extension, creating a tree of images.

The advantage is that base images allow scaling the development process. It becomes possible to split responsibilities between multiple teams or organizations. 
For example, one team is responsible for producing, testing and certifying a base OS stack, while another team adds applications or other product-specific
functions to the base image delivered by the first team. A third team could add QA and test tooling to the image produced by the second team.

To produce a base image, the XML definition for it should contain:

.. code:: xml

        <target>
                <package>
                        <base-image>
                                <name>base-rootfs.tgz</name>
                        </base-image>
                </package>
                ...
        </target>

This will produce a base-rootfs.tgz tarball as the output.

To produce an extended image, the XML definition for it should specify that a base image is required:

.. code:: xml

        <target>
                <debootstrap>
                        <type>base-image</type>
                </debootstrap>
                ...
        </target>

and a ``--base-image=/path/to/base/image`` command line option should be given to the ``elbe initvm submit`` command.

Full examples of base and extended image definitions are available in elbe source tree under tests/base-extended/simple-validation/
To use them, run the following commands:

Producing a base image:

::

    $ elbe initvm submit tests/base-extended/simple-validation/image-base.xml

Producing an extended image from the base image:

::

    $ elbe initvm submit --base-image $ELBE_BUILD/base-rootfs.tgz tests/base-extended/simple-validation/image-extended.xml

