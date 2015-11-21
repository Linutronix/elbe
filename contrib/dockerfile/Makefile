
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
		$(sshauth) \
		-d \
		-ti \
		--group-add kvm \
		--name \
		$(CONTAINERNAME) \
		$(IMAGENAME)

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
