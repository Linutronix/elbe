
# Dockerfile for elbe

[elbe][elb] is a debian based system to generate root-filesystems for embedded
devices.

[docker][doc] is an open-source project to easily create lightweight, portable,
self-sufficient containers from any application.

This is a Dockerfile to generate a elbe development environment for systems
other than debian based.

[doc]: https://www.docker.io "Docker Homepage"
[elb]: http://elbe-rfs.org   "ELBE Homepage"

## Depencies

You need docker installed and a running docker service.

## Build image

    % cd dockerfile
    % docker build -t own-elbe-system .

## start

Start a dettached docker session

    % docker run --privileged -d own-elbe-system

You get a Container-ID like this one

    a242543d614f8cd97729e8fe0c417897c769e6c381390d168f3fc39c0c497132

## connect

To connect to this container you get the ip with docker inspect.

    % docker inspect a242543d614f8c | grep IPAddress
    "IPAddress": "172.17.0.2",
    % ssh root@172.17.0.2

## passwords

    root: elbe
    elbe: elbe

