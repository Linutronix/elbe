# Dockerfile for elbe

<?
# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2014-2015 Silvio Fricke <silvio.fricke@gmail.com>
# SPDX-FileCopyrightText: 2018 Linutronix GmbH
?>

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

