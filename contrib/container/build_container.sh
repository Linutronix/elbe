#!/bin/bash

SCRIPT_DIR=$( dirname "${BASH_SOURCE[0]}")
echo "SCRIPT: $SCRIPT_DIR"
cd $SCRIPT_DIR

cd ../../
tar --exclude='contrib' -zcvf contrib/container/elbe.tar.gz .
cd contrib/container

if [ $# -ne 0 ]; then
    distro=$1    
else
    distro="debian:bookworm"
fi

rm -f Dockerfile_tmp
sed "s/debian:bookworm/${distro}/g" Dockerfile > Dockerfile_tmp
cp "sources_${distro}.list" sources.list

docker build \
    -f Dockerfile_tmp \
    -t elbe_container:testing .
