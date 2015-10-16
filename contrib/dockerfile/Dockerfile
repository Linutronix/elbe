# This Dockefile generate a image for the elbe buildsystem

# baseimage is debian wheezy
FROM debian:wheezy

# Maintainer
MAINTAINER Silvio Fricke <silvio.fricke@gmail.com>

# set debian/ubuntu config environment to noninteractive
ENV DEBIAN_FRONTEND noninteractive

# setup the initsystem
RUN dpkg-divert --local --rename --add /sbin/initctl && ln -sf /bin/true /sbin/initctl

# update and upgrade
RUN apt-get update -y && apt-get upgrade -y

# development base installation
RUN apt-get install -y git build-essential openssh-server vim supervisor sudo \
		       cpio python-mako python-lxml python-apt wget qemu kvm \
		       qemu-system qemu-kvm qemu-keymaps qemu-utils \
		       libvirt-bin qemu-utils qemu-system qemu-user-static \
		       e2tools python-mako python python-lxml python-apt \
		       p7zip-full make python-parted

# clean up
RUN apt-get clean

# additions
ADD adds/supervisord.conf /etc/supervisord.conf

# create elbe user
RUN useradd -d /home/elbe -U -G libvirt,kvm,libvirt-qemu -m -s /bin/bash -u 1000 elbe
RUN echo "root:elbe" | chpasswd
RUN echo "elbe:elbe" | chpasswd

# sudo for elbe
RUN echo "%elbe  ALL=(ALL:ALL) NOPASSWD: ALL" > /etc/sudoers.d/elbegrp
RUN chmod 0440 /etc/sudoers.d/elbegrp

# download git repository
RUN su --login elbe -c "git clone https://github.com/Linutronix/elbe.git"

# ssh and startup configuration
RUN mkdir -v /var/run/sshd
CMD ["/usr/bin/supervisord", "-n"]
EXPOSE 22
