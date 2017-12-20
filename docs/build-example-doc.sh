#!/bin/bash
#
# ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (c) 2013, 2015-2017 Manuel Traut <manut@linutronix.de>
#
# SPDX-License-Identifier: GPL-3.0-or-later

FILES=`ls -1 ../examples`
DEST=elbe-examples.tmp
TXT=elbe-examples.txt
rm -f $DEST

echo $FILES

echo "ELBE examples" >>$DEST
echo "=============" >> $DEST
echo "" >> $DEST
for F in $FILES; do
	../elbe show ../examples/$F >> $DEST
	echo "" >> $DEST
done

cat $DEST | sed -e s?'../examples/'?''? > $TXT
