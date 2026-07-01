# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2015 Silvio Fricke <silvio.fricke@gmail.com>
# SPDX-FileCopyrightText: 2018 Linutronix GmbH

IMAGENAME ?= elbe-devel-image
CONTAINERNAME ?= elbe-devel
KVMGID ?= $(shell ls -n /dev/kvm | awk '{ print $$4 }')
UID ?= $(shell id -u)

# Container engine to use. Defaults to podman if installed, else docker.
ENGINE ?= $(shell command -v podman >/dev/null 2>&1 && echo podman || echo docker)

# Common container run options
RUN_OPTS = \
	--cap-add SYS_ADMIN \
	--security-opt seccomp=unconfined \
	--security-opt apparmor=unconfined \
	--group-add kvm \
	--device /dev/kvm \
	--device /dev/fuse \
	--rm \
	--interactive \
	--tty

# Only meaningful for podman: map the invoking host user to the same UID
# inside the container's user namespace. Has no effect on docker. This is
# in addition to, not a replacement for, the @USERID@/@KVMGID@ template
# substitution below, which is still needed for the baked-in "elbe" user
# and its kvm-elbe group membership.
ifeq ($(ENGINE),podman)
RUN_OPTS += --userns=keep-id
endif

# container commands
build:
	test -c /dev/kvm  || ( echo "/dev/kvm not found" && false )
	test -c /dev/fuse || ( echo "/dev/fuse not found" && false )
	test -n "$(KVMGID)" || ( echo "detecting groupid of /dev/kvm failed" && false )
	sed -e "s#@KVMGID@#$(KVMGID)#g" \
	    -e "s#@USERID@#$(UID)#g" \
	    Containerfile.in > Containerfile
	$(ENGINE) build --build-arg http_proxy=$(http_proxy) \
	             --build-arg https_proxy=$(https_proxy) \
	             --build-arg no_proxy=$(no_proxy) \
	             --no-cache \
                     -f Containerfile \
	             -t $(IMAGENAME) .
	rm Containerfile

start-devel:
	$(ENGINE) ps | grep $(CONTAINERNAME)$$ || \
	$(ENGINE) run --name $(CONTAINERNAME) \
		-e http_proxy=$(http_proxy) \
		-e https_proxy=$(https_proxy) \
		-e no_proxy=$(no_proxy) \
		-v $(realpath ../../.):/var/cache/elbe/devel -w /var/cache/elbe/devel \
		$(RUN_OPTS) \
		$(IMAGENAME)

start:
	$(ENGINE) ps | grep $(CONTAINERNAME)$$ || \
	$(ENGINE) run --name $(CONTAINERNAME) \
		-e http_proxy=$(http_proxy) \
		-e https_proxy=$(https_proxy) \
		-e no_proxy=$(no_proxy) \
		$(RUN_OPTS) \
		$(IMAGENAME)

stop:
	-$(ENGINE) stop $(CONTAINERNAME)

stoprm: stop
	-$(ENGINE) rm $(CONTAINERNAME)

clean: stoprm
	-$(ENGINE) rmi $(IMAGENAME)

connect: start
	$(ENGINE) exec -tiu $(UID) $(CONTAINERNAME) /bin/bash

.PHONY: build start stop stoprm clean connect
