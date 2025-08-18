FROM debian:bookworm

ARG USER="dev"

USER root

ENV DEBIAN_FRONTEND noninteractive

COPY sources.list /etc/apt/sources.list

RUN apt update

# install build tools, QEMU and Python
RUN apt -y install \
    openssh-server debootstrap reprepro python3 python3-pip python3-venv \
    binfmt-support qemu-user-static locales git apt python3-cherrypy3 sudo \
    python3-gpg python3-lxml python3-mako python3-passlib python3-pycdlib \
    python3-debian python3-suds python3-libvirt swig cpio patchelf \
    python3-beaker python3-spyne python3-sqlalchemy python3-parted \
    tmux dosfstools e2fsprogs xfsprogs file lsof vim

RUN dpkg --add-architecture arm64
RUN apt update

RUN apt -y install libc6:arm64

# setup locale
RUN echo "en_US.UTF-8 UTF-8" > /etc/locale.gen && locale-gen
ENV LANG en_US.UTF-8
ENV LANGUAGE en_US:en
ENV LC_ALL en_US.UTF-8

##### create user #####

ARG HOST_USER=1000
ARG HOST_GROUP=1000

# Create build user mathching outside UID and GID to avoid ownership issues
# and allow user to use sudo
RUN addgroup --gid $HOST_GROUP $USER && \
  useradd -rm -d /home/$USER -s /bin/bash -g $USER -G sudo -u $HOST_USER $USER && \
  echo "$USER ALL=(ALL:ALL) NOPASSWD:ALL" >> /etc/sudoers && \
  mkdir -p /home/$USER/.ssh && \
  chown -R $USER:$USER /home/$USER

# Prepare the elbe setup
RUN mkdir -p /var/cache/elbe
COPY source.xml /var/cache/elbe/
RUN mkdir -p /var/cache/elbe/installer
RUN mkdir -p /var/cache/elbe/devel

RUN mkdir -p /etc/ssh
RUN echo 'PermitRootLogin yes' >> /etc/ssh/sshd_config

# reduce container size
# RUN sudo apt clean -y

# copy repository keys
RUN mkdir -p /etc/apt/trusted.gpg.d/
COPY apt_keys/* /etc/apt/trusted.gpg.d/

# Copy bashrc
COPY bashrc /home/$USER/.bashrc
RUN chown $USER:$USER /home/$USER/.bashrc && chmod +x /home/$USER/.bashrc
COPY bashrc /root/.bashrc
RUN chown root:root /root/.bashrc && chmod +x /root/.bashrc

RUN chown $USER:$USER /var/cache/elbe

# copy scripts
COPY scripts/* /scripts/
RUN chmod +x /scripts/*

# Get elbe
ADD elbe.tar.gz /var/cache/elbe/devel

RUN mkdir -p /build/results/images

WORKDIR /var/cache/elbe
USER $USER

RUN PATH=$PATH:/var/cache/elbe/devel PYTHONPATH=$PYTHONPATH:/var/cache/elbe/devel elbe db init

CMD "bash"
