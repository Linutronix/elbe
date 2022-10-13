# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: Manuel Traut <manuel.traut@mt.com>

FROM debian:bullseye-slim

USER root

ENV DEBIAN_FRONTEND noninteractive


ENV LANG en_US.UTF-8
ENV LANGUAGE en_US:en
ENV LC_ALL en_US.UTF-8

RUN echo "deb http://ftp.debian.org/debian bullseye-backports main" >> /etc/apt/sources.list && \
    apt-get update -y && \
    apt-get install -y --no-install-recommends \
        elbe-archive-keyring

# install current elbe
RUN echo 'deb [signed-by=/usr/share/keyrings/elbe-archive-keyring.gpg] http://debian.linutronix.de/elbe bullseye main' > /etc/apt/sources.list.d/elbe.list && \
    apt-get update -y && \
    apt-get install -y --no-install-recommends \
        python3-elbe-buildenv \
	locales && \
    apt-get clean -y && \
    rm -rf /var/lib/apt/lists/*

RUN echo "en_US.UTF-8 UTF-8" > /etc/locale.gen && locale-gen

RUN echo "root:elbe" | chpasswd
