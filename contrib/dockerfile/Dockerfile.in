#
# ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (c) 2014-2015 Silvio Fricke <silvio.fricke@gmail.com>
# Copyright (c) 2018 Manuel Traut <manut@linutronix.de>
#
# SPDX-License-Identifier: GPL-3.0-or-later

# This Dockefile generate a image for the elbe buildsystem
FROM elbeproject/debian-stretch:latest

USER root
ENV DEBIAN_FRONTEND noninteractive

# use a sources.list including security
RUN echo "deb http://ftp.de.debian.org/debian stretch main" > /etc/apt/sources.list; \
    echo "deb http://security.debian.org/debian-security stretch/updates main" >> /etc/apt/sources.list

# update, upgrade and install elbe runtime-dependencies
RUN apt-get update -y ;\
    apt-get install -y --no-install-recommends \
                    -o Dpkg::Options::="--force-confnew" \
        systemd \
        ca-certificates \
        sudo \
        vim-nox \
        wget \
        software-properties-common \
        gnupg \
        python3-setuptools \
        python3-yaml \
        python3-jsonschema \
        locales \
        gcc \
        g++ \
        diffstat \
        texinfo \
        gawk \
        chrpath \
        python3-mako \
        fuseiso9660 \
        aptly \
        qemu-system-x86

RUN echo "en_US.UTF-8 UTF-8" > /etc/locale.gen && locale-gen

ENV LANG en_US.UTF-8
ENV LANGUAGE en_US:en
ENV LC_ALL en_US.UTF-8

# install current elbe
RUN apt-add-repository 'deb http://debian.linutronix.de/elbe stretch main'
RUN wget http://debian.linutronix.de/elbe/elbe-repo.pub
RUN apt-key add elbe-repo.pub
RUN apt-get update -y
RUN apt-get install -y --no-install-recommends \
        elbe \
        elbe-doc
RUN apt-get clean -y
RUN rm -rf /var/lib/apt/lists/*

# create elbe user
RUN groupadd -g @KVMGID@ -o -r kvm-elbe
RUN useradd -d /home/elbe -U -G kvm-elbe,libvirt -m -s /bin/bash -u @USERID@ elbe
RUN echo "root:elbe" | chpasswd
RUN echo "elbe:elbe" | chpasswd

RUN rm -f /lib/systemd/system/multi-user.target.wants/*;\
    rm -f /etc/systemd/system/*.wants/*;\
    rm -f /lib/systemd/system/local-fs.target.wants/*; \
    rm -f /lib/systemd/system/sockets.target.wants/*udev*; \
    rm -f /lib/systemd/system/sockets.target.wants/*initctl*; \
    rm -f /lib/systemd/system/basic.target.wants/*;\
    rm -f /lib/systemd/system/anaconda.target.wants/*;

VOLUME [ "/sys/fs/cgroup" ]
VOLUME [ "/elbe" ]
VOLUME [ "/var/cache/elbe" ]

# sudo for elbe
RUN echo "%elbe  ALL=(ALL:ALL) NOPASSWD: ALL" > /etc/sudoers.d/elbegrp
RUN chmod 0440 /etc/sudoers.d/elbegrp

# run qemu as root
RUN echo 'user = "root"' >> /etc/libvirt/qemu.conf
RUN echo 'group = "root"' >> /etc/libvirt/qemu.conf

# run libvirt in systemd on startup
RUN systemctl enable libvirtd

CMD [ "/lib/systemd/systemd" ]
