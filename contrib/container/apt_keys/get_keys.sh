#!/bin/bash

# Extract the apt keys form the docker containers.
CONTAINERS="ubuntu:24.04 ubuntu:22.04 debian:bookworm"

# extract the apt repo keys form the given containers
for CONTAINER in $CONTAINERS; do
    docker run -it --rm -v ${PWD}:/keys $CONTAINER \
    bash -c "cp /etc/apt/trusted.gpg.d/* /keys"
done

# dearmor all armored keys
for KEY in $(find . -name "*.asc"); do
    gpg --dearmor $KEY
done

# add elbe key
cp ../elbe.asc .
gpg --dearmor elbe.asc
