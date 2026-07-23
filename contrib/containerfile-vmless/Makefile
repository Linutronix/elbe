# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Linutronix GmbH

IMAGENAME ?= elbe-buildenv-image
CONTAINERNAME ?= elbe-buildenv

# Container engine to use. Defaults to podman if installed, else docker.
ENGINE ?= $(shell command -v podman >/dev/null 2>&1 && echo podman || echo docker)

# Common container run options
RUN_OPTS = \
	--cap-add SYS_ADMIN \
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
	$(ENGINE) build --build-arg http_proxy=$(http_proxy) \
	             --build-arg https_proxy=$(https_proxy) \
	             --build-arg no_proxy=$(no_proxy) \
	             -t $(IMAGENAME) .

# Builds the elbe .deb packages from this checkout first
build-local:
	$(ENGINE) build --build-arg http_proxy=$(http_proxy) \
	             --build-arg https_proxy=$(https_proxy) \
	             --build-arg no_proxy=$(no_proxy) \
	             -f Containerfile.local \
	             -t $(IMAGENAME) ../..

start:
	$(ENGINE) ps | grep $(CONTAINERNAME)$$ || \
	$(ENGINE) run -d --name $(CONTAINERNAME) \
		-e http_proxy=$(http_proxy) \
		-e https_proxy=$(https_proxy) \
		-e no_proxy=$(no_proxy) \
		-v $(CURDIR):/build:Z \
		$(RUN_OPTS) \
		$(IMAGENAME) elbe daemon --host 127.0.0.1

stop:
	-$(ENGINE) stop $(CONTAINERNAME)

stoprm: stop
	-$(ENGINE) rm $(CONTAINERNAME)

clean: stoprm
	-$(ENGINE) rmi $(IMAGENAME)

connect: start
	$(ENGINE) exec -ti $(CONTAINERNAME) /bin/bash

.PHONY: build build-local start stop stoprm clean connect
