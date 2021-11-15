# ELBE development container

[//]: # "Copyright (c) 2021 Daniel Braunwarth <daniel@braunwarth.dev>"
[//]: # "SPDX-License-Identifier: GPL-3.0-or-later"

This container is intended to build and run ELBE from Git sources.

To build and run the container [Podman](https://podman.io/) should be used.

The container is based on the official Debian Bullseye image in the slim
variant.

## Dependencies

To be able to build and use this container you need:

- [Make](https://www.gnu.org/software/make/)
- [Podman](https://podman.io/)

  See <https://podman.io/getting-started/> for information how to get started
  with Podman.

## Security

Unfortunately podman cannot be used in rootless mode, because ELBE needs the
`CAP_SYS_ADMIN` capability to be able to facilitate QEMU.

At the moment the container is started in privileged mode. This should be
restricted in the future.

## Usage

### Build container image

To build the container image run:

```shell
sudo make build
```

The resulting image is named `elbe-devel`.

### Start container

To start the container run:

```shell
sudo make start
```

The started container is named `elbe-devel`. It is not possible to start
multiple container instances.

### Stop container

To stop the container run:

```shell
sudo make stop
```

### Attach to running container

To attach to a running container run:

```shell
sudo make attach
```

The default working directory is `/usr/src`. This is where the Git repository
is mounted to.

### Build initvm

To build an initvm attach to the running container and run:

```shell
./elbe initvm --devel create elbepack/init/initvm-ssh-root-open-danger.xml
```

To be able to sync the ELBE sources between the Git repository and the initvm
we must be able to connect to the initvm via SSH as root user. For this reason
we are using `elbepack/init/initvm-ssh-root-open-danger.xml`.

### Add already existing initvm to container

To add an already existing initvm to a newly created container instance attach
to the running container and run:

```shell
virsh --connect qemu:///system define initvm/libvirt.xml
```

### Update ELBE in initvm

To update the used ELBE sources in an initvm run:

```shell
./elbe initvm --devel sync
```

### Clean-up

To remove the container instance and image run:

```shell
sudo make clean
```
