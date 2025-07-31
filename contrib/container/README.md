# Elbe Docker container

This container allows to use elbe without a initvm.

Building for foreign CPU architectures is supported if the host is able to load the binfmt_misc kernel module.

## Build the container

- First get the Debian, Ubuntu and Elbe apt repository signing keys by running: `contrib/container/apt_keys/get_keys.sh`.
- Then build the container by running `contrib/container/build_container.sh`.
  This script expects that you have cloned the git repository, i.e. that the elbe sources can be found at `../../`

## Use the container

Run `contrib/container/run_container.sh` to start the container.

This script read-only bind-mounts the example images to `/images` in the container.
The `.bashrc` is used to mount and writeable overlay at `/tmp/images`.

The `initvm` commands are not supported in the container, but you can use `build_image` instead:
```bash
Usage: build_image
   [ -c | --build-sdk ]
   [ -r | --result-path ]
   -i | --image path/to/image/xml
```

You can find this and other scripts available in the container at `contrib/container/scripts`.

## More information

- The elbe Docker container _simulates_ and elbe initvm. Please be aware that this means the kernel of the host OS is used and may have an impact on the build result, e.g. with respect to used filesystem drivers.
- Since elbe is not modified, the _initvm_ command will not work since no libvirt or QEMU VM is available.
- The container uses [qemu and bimfmt](https://wiki.debian.org/QemuUserEmulation) to allow building images for foreign architectures, which is the same mechanism as used by the elbe initvm. To use this, the kernel module *binfmt_misc* needs to be loaded. This is done in the *run_container.sh* script, but the module must be available and the user needs sudo rights.
- The container needs to be a _privileged_ container, for _binfmt_ but also for different _mount_ operations needed during the image build.
- The container also needs to bind-mount _dev_ form the host environment, else new devices created by _losetup_ will not show up, and the build will fail.

## Known issues

- Elbe initvm and related commands doesn't work.
- Building ISO images doesn't work
