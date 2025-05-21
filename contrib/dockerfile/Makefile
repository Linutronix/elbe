# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2015 Silvio Fricke <silvio.fricke@gmail.com>
# SPDX-FileCopyrightText: 2018 Linutronix GmbH

DOCKERFILE ?= Dockerfile
TAG ?= latest
ifneq ($(TAG),latest)
DOCKERFILE = Dockerfile-$(TAG)
endif

IMAGENAME ?= elbe-devel-image
CONTAINERNAME ?= elbe-devel-$(TAG)
KVMGID ?= $(shell ls -n /dev/kvm | awk '{ print $$4 }')
UID ?= $(shell id -u)

PROJECTDIR ?= $(shell pwd)/../../

# docker commands
build:
	test -c /dev/kvm  || ( echo "/dev/kvm not found" && false )
	test -c /dev/fuse || ( echo "/dev/fuse not found" && false )
	test -n "$(KVMGID)" || ( echo "detecting groupid of /dev/kvm failed" && false )
	sed -e "s#@KVMGID@#$(KVMGID)#g" \
	    -e "s#@USERID@#$(UID)#g" \
	    $(DOCKERFILE).in > $(DOCKERFILE)
	docker build --build-arg http_proxy=$(http_proxy) \
	             --build-arg https_proxy=$(https_proxy) \
	             --build-arg no_proxy=$(no_proxy) \
	             --no-cache \
	             --file $(DOCKERFILE) \
	             -t $(IMAGENAME):$(TAG) $(PROJECTDIR)
	rm $(DOCKERFILE)

start:
	docker ps | grep $(CONTAINERNAME)$$ || \
	docker run --name $(CONTAINERNAME) -d \
		-e container=docker \
		-e http_proxy=$(http_proxy) \
		-e https_proxy=$(https_proxy) \
		-e no_proxy=$(no_proxy) \
		-v $(realpath ../../.):/elbe -w /elbe\
		-v /sys/fs/cgroup:/sys/fs/cgroup:ro \
		--cap-add SYS_ADMIN \
		--security-opt seccomp:unconfined \
		--security-opt apparmor:unconfined \
		--group-add kvm \
		--device /dev/kvm \
		--device /dev/fuse \
		$(IMAGENAME):$(TAG)

stop:
	-docker stop $(CONTAINERNAME)

stoprm: stop
	-docker rm $(CONTAINERNAME)

clean: stoprm
	-docker rmi $(IMAGENAME):$(TAG)

connect: start
	docker exec -tiu $(UID) $(CONTAINERNAME) /bin/bash

.PHONY: build start stop stoprm clean connect
