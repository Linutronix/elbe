FROM debian:bullseye-slim

USER root

ENV DEBIAN_FRONTEND noninteractive


ENV LANG en_US.UTF-8
ENV LANGUAGE en_US:en
ENV LC_ALL en_US.UTF-8

RUN apt-get update -y && \
    apt-get install -y --no-install-recommends \
        wget gnupg2

# install current elbe
RUN echo 'deb http://debian.linutronix.de/elbe buster main' > /etc/apt/sources.list.d/elbe.list && \
    wget http://debian.linutronix.de/elbe/elbe-repo.pub && \
    apt-key add elbe-repo.pub && \
    apt-get update -y && \
    apt-get install -y --no-install-recommends \
        python3-elbe-buildenv \
	locales && \
    apt-get clean -y && \
    rm -rf /var/lib/apt/lists/*

RUN echo "en_US.UTF-8 UTF-8" > /etc/locale.gen && locale-gen

RUN echo "root:elbe" | chpasswd
