#! /bin/bash
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2023 Linutronix GmbH

ARCH="$(dpkg-architecture -q DEB_BUILD_ARCH)"
DIST="$(. /etc/os-release; echo ${VERSION_CODENAME/*, /})"

cd repo
reprepro list "$DIST" | awk '{print "sudo apt-get install -y "$2}' | sh
