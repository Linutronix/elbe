# This Dockefile generate a image for the elbe buildsystem

# baseimage is debian wheezy
FROM debian:jessie

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
        libvirt-bin \
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
RUN useradd -d /home/elbe -U -G libvirt,kvm,kvm78,libvirt-qemu -m -s /bin/bash -u 1000 elbe
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
CMD ["/usr/bin/supervisord", "-n"]
EXPOSE 22
