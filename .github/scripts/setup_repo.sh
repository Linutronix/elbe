#! /bin/bash
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2023 Linutronix GmbH

ARCH="$(dpkg-architecture -q DEB_BUILD_ARCH)"
DIST="$(. /etc/os-release; echo ${VERSION_CODENAME/*, /})"

mkdir repo
cp -a .github/templates/reprepro/* repo
cd repo

find . -type f -exec sed -i -e "s/@ARCH@/${ARCH}/" -e "s/@DIST@/${DIST}/" {} \;

reprepro --ignore=wrongdistribution include "$DIST" ../../*_${ARCH}.changes
