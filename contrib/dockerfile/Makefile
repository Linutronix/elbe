# ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (c) 2015 Silvio Fricke <silvio.fricke@gmail.com>
# Copyright (c) 2018 Manuel Traut <manut@linutronix.de>
#
# SPDX-License-Identifier: GPL-3.0-or-later

IMAGENAME ?= elbe-image
CONTAINERNAME ?= elbe

ifdef SSH_AUTH_SOCK
	sshauth = -e SSH_AUTH_SOCK=/ssh-auth-sock -v $(SSH_AUTH_SOCK):/ssh-auth-sock
endif

# docker commands
build:
	docker build -t $(IMAGENAME) .

run:
	docker run \
		-v $(realpath ../../.):/elbe \
		--device /dev/kvm:/dev/kvm \
		-v /sys/fs/cgroup:/sys/fs/cgroup:ro \
		--cap-add SYS_ADMIN \
		--security-opt seccomp:unconfined \
		--tmpfs /tmp \
		--tmpfs /run \
		--tmpfs /run/lock \
		-e container=docker \
		$(sshauth) \
		-d \
		-ti \
		--group-add kvm \
		--name \
		$(CONTAINERNAME) \
		$(IMAGENAME) \
		/lib/systemd/systemd

getip:
	docker inspect -f '{{ .NetworkSettings.IPAddress }}' $(CONTAINERNAME)

start: run getip

stop:
	docker stop $(CONTAINERNAME)

stoprm: stop
	docker rm $(CONTAINERNAME)

# ssh related functions
cleanssh:
	IP=$(shell docker inspect -f '{{ .NetworkSettings.IPAddress }}' ${CONTAINERNAME}) ;\
	[[ -n "$${IP}" ]] && ssh-keygen -R $${IP}

connect:
	SBC=$(shell which sbc) ;\
	IP=$(shell docker inspect -f '{{ .NetworkSettings.IPAddress }}' ${CONTAINERNAME}) ;\
	ssh-copy-id elbe@$${IP} ;\
	$$SBC ssh -XA elbe@$${IP}
