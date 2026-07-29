Add a ``<file-command>`` fs-finetuning option that runs a command against
the just-created partition image file, for commands like ``veritysetup format``
that operate on a plain file. Unlike ``<device-command>``, it never requires a
loop device, so it is safe to use in rootless container builds.
