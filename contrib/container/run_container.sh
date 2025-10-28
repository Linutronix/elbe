#!/bin/bash

lsmod | grep binfmt_misc
if [ $? -ne 0 ]; then
    echo "Trying to load binfmt kernel module for cross-builds ..."
    sudo modprobe binfmt_misc
fi

echo "PWD: $PWD"
mkdir -p result
RESULT=$(realpath ./result)
echo "RESULT DIR: $RESULT"

SCRIPT_DIR=$(realpath "${BASH_SOURCE[0]}")
echo "SCRIPT: $SCRIPT_DIR"
IMAGES=$(realpath ../../examples)
echo "IMAGES: $IMAGES"

docker run --rm -it \
    -v ${HOME}/.ssh:/home/dev/.ssh:ro \
    -v ${IMAGES}:/images:ro \
    -v ${RESULT}:/build/results/images:rw \
     -v /dev:/dev \
    --privileged \
    elbe_container:testing
