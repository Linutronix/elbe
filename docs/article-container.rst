**********************
Building in Containers
**********************

The :doc:`elbe build <elbe-build>` command builds an ELBE project without an
initvm. As it does not provide any isolation of the build environment itself,
it is useful to run it inside a container.


Prepare Container
=================

The container definition in *contrib/containerfile/Containerfile(.local)*
provides a ready-to-use build environment for this.

-  Build the container image, installing elbe from the published elbe
   archive:

   ::

      $ cd contrib/containerfile
      $ make build

-  Alternatively, build the container image with ELBE packages
   built from the current checkout, instead of the published ones:

   ::

      $ cd contrib/containerfile
      $ make build-local


Run Build in Rootful Container
==============================

In order to use the full feature set of ELBE, elevated privileges are required.
In particular, these elevated privileges are needed for the following features:

-  ``<grub-install>``
-  ``<device-command>`` or ``<path-command>`` inside ``<fstab>``
   (including the related ``<tune2fs>``)
-  ``<mknod>`` inside ``<finetuning>``
-  a ``<losetup>`` project-finetuning action containing
   ``copy_from_partition``, ``copy_to_partition``, or ``command``

To enable them, a full build command could look like this:

   ::

      pkexec podman run --rm \
            -v $(pwd):/work:Z \
            --cap-add SYS_ADMIN \
            --cap-add MKNOD \
            --device-cgroup-rule 'b *:* rmw' \
            --device /dev/loop-control \
            -v /dev:/dev \
            -v /run/udev:/run/udev:ro \
            --network host \
            --security-opt apparmor=unconfined \
            elbe-buildenv-image \
            elbe build /work/myimage.xml --build-dir /work/build


These elevated privileges expose several potential attack vectors, and
containerization does not mitigate these risks compared to performing
the build directly on the host. Therefore, in this scenario,
containerization should not be considered a security feature, but solely
as a means of simplifying the environment setup.
