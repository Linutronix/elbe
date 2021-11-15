# ELBE development container
# Copyright (c) 2021 Daniel Braunwarth <daniel@braunwarth.dev>
#
# SPDX-License-Identifier: GPL-3.0-or-later

build:
	podman image build --tag elbe-devel .

start:
	podman container list | grep elbe-devel || \
	podman container run \
		--name elbe-devel \
		--detach \
		--rm \
		--volume $(shell git rev-parse --show-toplevel):/usr/src \
		--workdir /usr/src \
		--privileged \
		elbe-devel

stop:
	podman container stop --ignore elbe-devel

attach: start
	podman container exec \
		--tty \
		--interactive \
		elbe-devel \
		/bin/bash

clean: stop
	podman image rm --force elbe-devel || true

.PHONY: build start stop clean atach
