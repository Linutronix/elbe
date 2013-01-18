#!/bin/bash
FILES=`ls -1 ../examples`
DEST=elbe-examples.txt
rm -f $DEST
echo "ELBE examples" >>$DEST
echo "=============" >> $DEST
echo "" >> $DEST
for F in $FILES; do
	../elbe show ../examples/$F >> $DEST
done
