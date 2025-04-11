# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2015 Silvio Fricke <silvio.fricke@gmail.com>
# SPDX-FileCopyrightText: 2018 Linutronix GmbH

IMAGENAME ?= elbe-devel-image
CONTAINERNAME ?= elbe-devel
KVMGID ?= $(shell ls -n /dev/kvm | awk '{ print $$4 }')
UID ?= $(shell id -u)

# Common docker run options
DOCKER_RUN_OPTS = \
	--cap-add SYS_ADMIN \
	--security-opt seccomp:unconfined \
	--security-opt apparmor:unconfined \
	--group-add kvm \
	--device /dev/kvm \
	--device /dev/fuse \
	--rm \
	--interactive \
	--tty

# docker commands
build:
	test -c /dev/kvm  || ( echo "/dev/kvm not found" && false )
	test -c /dev/fuse || ( echo "/dev/fuse not found" && false )
	test -n "$(KVMGID)" || ( echo "detecting groupid of /dev/kvm failed" && false )
	sed -e "s#@KVMGID@#$(KVMGID)#g" \
	    -e "s#@USERID@#$(UID)#g" \
	    Dockerfile.in > Dockerfile
	docker build --build-arg http_proxy=$(http_proxy) \
	             --build-arg https_proxy=$(https_proxy) \
	             --build-arg no_proxy=$(no_proxy) \
	             --no-cache \
	             -t $(IMAGENAME) .
	rm Dockerfile

start-devel:
	docker ps | grep $(CONTAINERNAME)$$ || \
	docker run --name $(CONTAINERNAME) \
		-e http_proxy=$(http_proxy) \
		-e https_proxy=$(https_proxy) \
		-e no_proxy=$(no_proxy) \
		-v $(realpath ../../.):/var/cache/elbe/devel -w /var/cache/elbe/devel \
		$(DOCKER_RUN_OPTS) \
		$(IMAGENAME)

start:
	docker ps | grep $(CONTAINERNAME)$$ || \
	docker run --name $(CONTAINERNAME) \
		-e http_proxy=$(http_proxy) \
		-e https_proxy=$(https_proxy) \
		-e no_proxy=$(no_proxy) \
		$(DOCKER_RUN_OPTS) \
		$(IMAGENAME)

stop:
	-docker stop $(CONTAINERNAME)

stoprm: stop
	-docker rm $(CONTAINERNAME)

clean: stoprm
	-docker rmi $(IMAGENAME)

connect: start
	docker exec -tiu $(UID) $(CONTAINERNAME) /bin/bash

.PHONY: build start stop stoprm clean connect
