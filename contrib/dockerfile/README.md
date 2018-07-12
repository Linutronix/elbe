# Dockerfile for elbe
#
# ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (c) 2014-2015 Silvio Fricke <silvio.fricke@gmail.com>
# Copyright (c) 2018 Manuel Traut <manut@linutronix.de>
#
# SPDX-License-Identifier: GPL-3.0-or-later

[elbe][elb] is a debian based system to generate root-filesystems for embedded
devices.

[docker][doc] is an open-source project to easily create lightweight, portable,
self-sufficient containers from any application.

This is a Dockerfile to generate a elbe development and runtime environment for
systems other than debian based.

[doc]: https://www.docker.io "Docker Homepage"
[elb]: http://elbe-rfs.org   "ELBE Homepage"

## Dependencies

You need docker installed, a running docker service and `make` installed.


## usage

A `Makefile` with some handy targets are provided. Per default the image name
is `elbe-image` and a started container name is `elbe`. This names are
changeable via `IMAGENAME` and `CONTAINERNAME` environment variables.

* `build`: build the image
* `start` start a container, mounts the elbe git-archive to `/elbe`
* `stop`: stop a running container
* `stoprm`: stop and remove the container
* `connect`: attach to a running container

After `connect` you can find the elbe git repository under `/elbe`.

## passwords

    root: elbe
    elbe: elbe

