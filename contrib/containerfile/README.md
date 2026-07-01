# Dockerfile for elbe

<?
# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2014-2015 Silvio Fricke <silvio.fricke@gmail.com>
# SPDX-FileCopyrightText: 2018 Linutronix GmbH
?>

[elbe][elb] is a debian based system to generate root-filesystems for embedded
devices.

[docker][doc] and [podman][pod] are open-source projects to easily create
lightweight, portable, self-sufficient containers from any application.

This is a Containerfile to generate an ELBE development and runtime environment for
systems that are not Debian based or where you prefer a clean separation.

[doc]: https://www.docker.io "Docker Homepage"
[pod]: https://podman.io     "Podman Homepage"
[elb]: http://elbe-rfs.org   "ELBE Homepage"

## Dependencies

You need `podman` or `docker` installed, plus `make`. `podman` is used by
default if it is found on the `PATH`; set `ENGINE=docker` to force Docker
instead (e.g. `make ENGINE=docker build`).

## usage

A `Makefile` with some handy targets are provided. Per default the image name
is `elbe-devel-image` and a started container name is `elbe-devel`. This names are
changeable via `IMAGENAME` and `CONTAINERNAME` environment variables.

* `build`: build the image
* `start` start a container, and use packaged elbe
* `start-devel` start a container, mounts the elbe git-archive to `/var/cache/elbe`
* `stop`: stop a running container
* `stoprm`: stop and remove the container
* `connect`: attach a new terminal to a running container

After `connect` you can find the elbe git repository under `/elbe`.

## passwords

    root: elbe
    elbe: elbe

