#!/bin/sh
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Linutronix GmbH
set -e

# Check if we already have CAP_SYS_ADMIN
# In that case we assume we are already running rootful,
# so no need for unshare.
capeff=$(grep '^CapEff:' /proc/self/status | cut -f2)
if [ $(( 0x$capeff & 0x200000 )) -ne 0 ]; then
    exec "$@"
fi

exec unshare --user --map-root-user --map-users=all --map-groups=all --mount -- "$@"
