#! /bin/bash
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2023 Linutronix GmbH

DIST="$(. /etc/os-release; echo ${VERSION_CODENAME/*, /})"

echo "deb [trusted=yes] file://$(pwd)/repo ${DIST} main" \
     > /etc/apt/sources.list.d/elbe.list

apt-get update
