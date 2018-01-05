#
# ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (c) 2014-2015 Silvio Fricke <silvio.fricke@gmail.com>
# Copyright (c) 2018 Manuel Traut <manut@linutronix.de>
#
# SPDX-License-Identifier: GPL-3.0-or-later

# This Dockefile generate a image for the elbe buildsystem
FROM debian:stretch

ENV LANG C.UTF-8

# update and upgrade
RUN export DEBIAN_FRONTEND noninteractive ;\
    apt-get update -y ;\
    apt-get install -y --no-install-recommends \
        build-essential \
        ca-certificates \
        cpio \
        e2tools \
        git \
        kvm \
        libvirt-daemon \
        libvirt-daemon-system \
        make \
        openssh-server \
        p7zip-full \
        python python-lxml \
        python-apt \
        python-apt \
        python-lxml \
        python-mako \
        python-mako \
        python-parted \
        python-suds \
        python-libvirt \
        qemu \
        qemu-keymaps \
        qemu-kvm \
        qemu-system \
        qemu-system \
        qemu-user-static \
        qemu-utils \
        qemu-utils \
        sudo \
        supervisor \
        tmux \
        vim \
        wget \
        ; \
    apt-get clean -y ;\
    rm -rf /var/lib/apt/lists/*

# additions
ADD adds/supervisord.conf /etc/supervisord.conf

# create elbe user
RUN groupadd -g 78 -o -r kvm78          # archlinux
RUN groupadd -g 124 -o -r kvm124        # debian-sid
RUN useradd -d /home/elbe -U -G libvirt,kvm,kvm78,kvm124,libvirt-qemu -m -s /bin/bash -u 1000 elbe
RUN echo "root:elbe" | chpasswd
RUN echo "elbe:elbe" | chpasswd

# sudo for elbe
RUN echo "%elbe  ALL=(ALL:ALL) NOPASSWD: ALL" > /etc/sudoers.d/elbegrp
RUN chmod 0440 /etc/sudoers.d/elbegrp

# add sbc (https://github.com/turicas/sbc)
ADD https://raw.githubusercontent.com/turicas/sbc/develop/sbc /usr/bin/sbc
RUN chmod a+rx /usr/bin/sbc

# ssh and startup configuration
RUN mkdir -v /var/run/sshd
CMD [ "/lib/systemd/systemd" ]
EXPOSE 22
