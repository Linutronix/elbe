
# Dockerfile for embedded linux build environment

## Build image

    cd dockerfile
    docker build -t own-elbe-system ./Dockerfile

## start

Start a dettached docker session

    docker run -d own-elbe-system

You get a Container-ID like this one

    a242543d614f8cd97729e8fe0c417897c769e6c381390d168f3fc39c0c497132

## connect

To connect to this container you get the ip with docker inspect.

    docker inspect a242543d614f8c | grep IPAddress
    "IPAddress": "172.17.0.2",

    ssh root@172.17.0.2

## passwords

    root: elbe
    elbe: elbe

